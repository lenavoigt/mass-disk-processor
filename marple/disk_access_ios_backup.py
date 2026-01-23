"""
iOS Backup Accessor for Marple

Provides access to iOS backups (encrypted or unencrypted) as if they were disk images.
Uses the iOSbackup library to parse the backup structure and decrypt files.

Password handling:
- Looks for a 'password.txt' file in the same directory as the backup
- If not found, the backup is skipped with a log message
"""

import os
import logging
import tempfile
from pathlib import Path

from marple.file_object import FileItem
from marple.partition_object import PartitionItem

try:
    from iOSbackup import iOSbackup
    from NSKeyedUnArchiver import unserializeNSKeyedArchiver
    IOS_BACKUP_AVAILABLE = True
except ImportError:
    IOS_BACKUP_AVAILABLE = False
    logging.warning("iOSbackup library not installed. iOS backup support unavailable.")


class iOSBackupError(Exception):
    """Exception raised for iOS backup access errors."""
    pass


class iOSBackupFileItem(FileItem):
    """
    Extended FileItem for iOS backup files.

    Stores additional iOS-specific metadata and handles reading from
    encrypted backup files via the iOSbackup library.
    """

    def __init__(self, full_path, inode, file_size, partition_sector,
                 backup_file_hash, domain, relative_path, manifest_blob, backup_accessor):
        super().__init__(full_path, inode, file_size, partition_sector)
        self.backup_file_hash = backup_file_hash  # SHA1 hash filename in backup
        self.domain = domain                       # e.g., 'HomeDomain', 'CameraRollDomain'
        self.relative_path = relative_path         # Original path within domain
        self._manifest_blob = manifest_blob        # Raw NSKeyedArchive blob for decryption
        self._backup_accessor = backup_accessor    # Reference to parent accessor
        self._decrypted_data = None                # Cache for decrypted content

    def read(self, size_to_read=None, fs_handle=None):
        """
        Read data from the iOS backup file.

        For iOS backups, fs_handle is ignored - we use the backup accessor instead.
        """
        if self.file_size == 0:
            return b''

        # Load full file content if not cached
        if self._decrypted_data is None:
            self._decrypted_data = self._backup_accessor._read_file_content(self)
            self._FileItem__bytes_read = 0  # Reset read position

        if size_to_read is None:
            # Return all data
            return self._decrypted_data
        else:
            # Sequential read support
            if self._FileItem__bytes_read >= len(self._decrypted_data):
                return b''
            end_pos = min(self._FileItem__bytes_read + size_to_read, len(self._decrypted_data))
            data = self._decrypted_data[self._FileItem__bytes_read:end_pos]
            self._FileItem__bytes_read = end_pos
            return data

    def clear_cache(self):
        """Clear cached decrypted data to free memory."""
        self._decrypted_data = None
        self._FileItem__bytes_read = 0


class iOSBackupAccessor:
    """
    Accessor for iOS backups that provides a similar interface to GenericDiskAccessor.

    iOS backups are treated as a single virtual partition containing all backup files
    with their original domain/path structure restored from the Manifest.db.
    """

    # Virtual partition sector for iOS backups (arbitrary, but consistent)
    VIRTUAL_PARTITION_SECTOR = 0

    def __init__(self, path_to_backup):
        """
        Initialize the iOS backup accessor.

        Args:
            path_to_backup: Path to the iOS backup directory (containing Manifest.db, etc.)

        Raises:
            iOSBackupError: If the backup cannot be accessed or password is missing
        """
        if not IOS_BACKUP_AVAILABLE:
            raise iOSBackupError("iOSbackup library not installed. Install with: pip install iOSbackup")

        if not os.path.isdir(path_to_backup):
            raise iOSBackupError(f"iOS backup path is not a directory: {path_to_backup}")

        self.path_to_backup = os.path.abspath(path_to_backup)
        self.path_to_image = self.path_to_backup  # Compatibility alias

        # Check for required files
        manifest_db = os.path.join(path_to_backup, 'Manifest.db')
        manifest_plist = os.path.join(path_to_backup, 'Manifest.plist')

        if not os.path.exists(manifest_db):
            raise iOSBackupError(f"Manifest.db not found in {path_to_backup}")
        if not os.path.exists(manifest_plist):
            raise iOSBackupError(f"Manifest.plist not found in {path_to_backup}")

        # Check if backup is encrypted and load password
        self._password = None
        self._is_encrypted = self._check_encryption_status()

        if self._is_encrypted:
            self._password = self._load_password()
            if self._password is None:
                raise iOSBackupError(
                    f"Encrypted backup requires password.txt in backup directory or parent. "
                    f"Backup path: {path_to_backup}"
                )

        # Initialize backup object
        self._backup = None
        self._init_backup()

        # File list cache
        self.list_of_files = None
        self.list_of_dir_inodes = []

        logging.info(f"iOS backup accessor initialized for: {path_to_backup}")

    def _check_encryption_status(self):
        """Check if the backup is encrypted by reading Manifest.plist."""
        import plistlib
        manifest_plist = os.path.join(self.path_to_backup, 'Manifest.plist')
        try:
            with open(manifest_plist, 'rb') as f:
                plist = plistlib.load(f)
            return plist.get('IsEncrypted', False)
        except Exception as e:
            logging.warning(f"Could not read Manifest.plist: {e}")
            # Assume encrypted if we can't read the plist
            return True

    def _load_password(self):
        """
        Load password from password.txt file.

        Looks for password.txt in:
        1. The backup directory itself
        2. The parent directory of the backup

        Returns:
            Password string or None if not found
        """
        # Check in backup directory
        password_file = os.path.join(self.path_to_backup, 'password.txt')
        if os.path.exists(password_file):
            return self._read_password_file(password_file)

        # Check in parent directory
        parent_dir = os.path.dirname(self.path_to_backup)
        password_file = os.path.join(parent_dir, 'password.txt')
        if os.path.exists(password_file):
            return self._read_password_file(password_file)

        logging.warning(f"No password.txt found for encrypted backup: {self.path_to_backup}")
        return None

    def _read_password_file(self, path):
        """Read password from file, stripping whitespace."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                password = f.read().strip()
            logging.info(f"Password loaded from: {path}")
            return password
        except Exception as e:
            logging.error(f"Error reading password file {path}: {e}")
            return None

    def _init_backup(self):
        """Initialize the iOSbackup object."""
        try:
            # Get the backup UDID (directory name)
            udid = os.path.basename(self.path_to_backup)
            backup_root = os.path.dirname(self.path_to_backup)

            if self._is_encrypted:
                self._backup = iOSbackup(
                    udid=udid,
                    cleartextpassword=self._password,
                    backuproot=backup_root
                )
            else:
                self._backup = iOSbackup(
                    udid=udid,
                    backuproot=backup_root
                )

            logging.info("iOSbackup object initialized successfully")

        except Exception as e:
            raise iOSBackupError(f"Failed to initialize iOS backup: {e}")

    @property
    def files(self):
        """Return list of FileItem objects for all files in the backup."""
        if self.list_of_files is None:
            self.list_of_files = []
            self._populate_file_list()
        return self.list_of_files

    @property
    def partitions(self):
        """
        Return list of partition objects.

        iOS backups are treated as a single virtual partition.
        """
        partition = PartitionItem(
            start=self.VIRTUAL_PARTITION_SECTOR,
            end=self.VIRTUAL_PARTITION_SECTOR,
            partition_type='iOS Backup',
            allocated=True
        )
        partition.files = self.files
        return [partition]

    def _populate_file_list(self):
        """Populate the list of files from the backup manifest."""
        try:
            # Get list of all files in the backup
            backup_files = self._backup.getBackupFilesList()

            inode_counter = 0
            for file_info in backup_files:
                # file_info contains: name, backupFile, domain, fileID, relativePath, flags, file (metadata blob)
                backup_file_hash = file_info.get('backupFile', '')
                domain = file_info.get('domain', '')
                relative_path = file_info.get('relativePath', '')

                # Skip entries without a file hash
                if not backup_file_hash:
                    continue

                # Get file metadata by deserializing the NSKeyedArchive plist
                file_metadata = {}
                file_metadata_blob = file_info.get('file')
                if file_metadata_blob:
                    try:
                        file_metadata = unserializeNSKeyedArchiver(file_metadata_blob)
                    except Exception as e:
                        logging.debug(f"Could not parse metadata for {backup_file_hash}: {e}")
                        file_metadata = {}

                file_size = file_metadata.get('Size', 0) if file_metadata else 0

                # Skip directories (Mode with S_IFDIR flag set, or Size=0 with no relativePath)
                # Mode 16877 = 0o40755 = directory with rwxr-xr-x permissions
                mode = file_metadata.get('Mode', 0)
                is_directory = (mode & 0o170000) == 0o040000  # S_IFDIR check

                if is_directory:
                    continue

                # Construct the full path as domain/relativePath
                full_path = f"{domain}/{relative_path}" if relative_path else domain

                # Create FileItem
                file_item = iOSBackupFileItem(
                    full_path=full_path,
                    inode=inode_counter,
                    file_size=file_size,
                    partition_sector=self.VIRTUAL_PARTITION_SECTOR,
                    backup_file_hash=backup_file_hash,
                    domain=domain,
                    relative_path=relative_path,
                    manifest_blob=file_info.get('file'),  # Store raw blob for decryption
                    backup_accessor=self
                )

                # Extract timestamps if available
                if file_metadata:
                    # iOS backup timestamps are not applicable
                    file_item.timestamps['m_time'] = None
                    file_item.timestamps['a_time'] = None
                    file_item.timestamps['cr_time'] = None

                file_item.path_to_disk_image = self.path_to_backup

                self.list_of_files.append(file_item)
                inode_counter += 1

            logging.info(f"Populated {len(self.list_of_files)} files from iOS backup")

        except Exception as e:
            logging.error(f"Error populating file list: {e}")
            raise iOSBackupError(f"Failed to read backup manifest: {e}")

    def _read_file_content(self, file_item):
        """
        Read and decrypt file content from the backup.

        Args:
            file_item: iOSBackupFileItem to read

        Returns:
            Decrypted file content as bytes
        """
        try:
            # Build manifest entry dict for getFileDecryptedCopy
            # The 'manifest' key must contain the raw NSKeyedArchive blob
            manifest_entry = {
                'fileID': file_item.backup_file_hash,
                'domain': file_item.domain,
                'relativePath': file_item.relative_path,
                'manifest': file_item._manifest_blob
            }

            # Get decrypted copy of the file using manifestEntry
            result = self._backup.getFileDecryptedCopy(
                manifestEntry=manifest_entry,
                temporary=True
            )

            if result and 'decryptedFilePath' in result:
                temp_path = result['decryptedFilePath']
                if os.path.exists(temp_path):
                    with open(temp_path, 'rb') as f:
                        data = f.read()
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    return data

            logging.warning(f"Could not decrypt file: {file_item.full_path}")
            return b''

        except Exception as e:
            logging.error(f"Error reading file {file_item.full_path}: {e}")
            return b''

    def get_file_system_handles(self):
        """
        Return a dictionary of file system handles.

        For iOS backups, we return a simple dict with a reference to self,
        though FileItem.read() handles file access directly.
        """
        return {self.VIRTUAL_PARTITION_SECTOR: self}

    def get_list_of_files(self, list_of_files):
        """
        Populate and return list of files.

        This method is provided for compatibility with GenericDiskAccessor interface.
        """
        self.list_of_files = list_of_files
        self._populate_file_list()
        return self.list_of_files

    def get_media_size(self):
        """
        Return total size of all files in the backup.

        Note: This is an approximation as iOS backups don't have a fixed media size.
        """
        total_size = sum(f.file_size for f in self.files)
        return total_size

    @property
    def is_encrypted(self):
        """Return whether the backup is encrypted."""
        return self._is_encrypted

    @property
    def device_info(self):
        """Return device information from the backup."""
        try:
            import plistlib
            info_plist = os.path.join(self.path_to_backup, 'Info.plist')
            if os.path.exists(info_plist):
                with open(info_plist, 'rb') as f:
                    return plistlib.load(f)
        except Exception as e:
            logging.warning(f"Could not read Info.plist: {e}")
        return {}


def is_ios_backup(path):
    """
    Check if a given path is an iOS backup directory.

    Args:
        path: Path to check

    Returns:
        True if the path appears to be an iOS backup, False otherwise
    """
    if not os.path.isdir(path):
        return False

    # Check for required iOS backup files
    manifest_db = os.path.join(path, 'Manifest.db')
    manifest_plist = os.path.join(path, 'Manifest.plist')

    return os.path.exists(manifest_db) and os.path.exists(manifest_plist)
