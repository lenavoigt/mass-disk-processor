"""
Android Backup Accessor for Marple

Provides access to Android backup (.ab) files as if they were disk images/filesystems.
Android backups contain a text header followed by zlib-compressed tar data.

Supports:
- Unencrypted backups (encryption: none)
- Encrypted backups (encryption: AES-256) - looks for password.txt

File format:
- Line 1: "ANDROID BACKUP"
- Line 2: Format version (integer)
- Line 3: Compression flag (1 = compressed)
- Line 4: Encryption type ("none" or "AES-256")
- For encrypted: 5 additional lines with crypto parameters
- Payload: zlib-compressed tar data (optionally AES-256 encrypted first)

Password handling for encrypted backups:
- Looks for 'password.txt' in the same directory as the .ab file
- Falls back to 'password.txt' in the parent directory
- Password file should contain the password on the first line
"""

import os
import io
import logging
import tarfile
import zlib
import hashlib

from marple.file_object import FileItem
from marple.partition_object import PartitionItem


class AndroidBackupError(Exception):
    """Exception raised for Android backup access errors."""
    pass


class AndroidBackupFileItem(FileItem):
    """
    Extended FileItem for files within Android backups.

    Handles reading file content from the decompressed tar data.
    """

    def __init__(self, full_path, inode, file_size, partition_sector, tar_member_name, backup_accessor):
        super().__init__(full_path, inode, file_size, partition_sector)
        self._tar_member_name = tar_member_name
        self._backup_accessor = backup_accessor
        self._cached_data = None

    def read(self, size_to_read=None, fs_handle=None):
        """
        Read data from the Android backup file.

        For Android backups, fs_handle is ignored - we use the backup accessor instead.
        """
        if self.file_size == 0:
            return b''

        # Load full file content if not cached
        if self._cached_data is None:
            self._cached_data = self._backup_accessor._read_file_content(self)
            self._FileItem__bytes_read = 0

        if self._cached_data is None:
            return b''

        if size_to_read is None:
            return self._cached_data
        else:
            if self._FileItem__bytes_read >= len(self._cached_data):
                return b''
            end_pos = min(self._FileItem__bytes_read + size_to_read, len(self._cached_data))
            data = self._cached_data[self._FileItem__bytes_read:end_pos]
            self._FileItem__bytes_read = end_pos
            return data

    def clear_cache(self):
        """Clear cached file data to free memory."""
        self._cached_data = None
        self._FileItem__bytes_read = 0


class AndroidBackupAccessor:
    """
    Accessor for Android backup (.ab) files.

    Provides a similar interface to GenericDiskAccessor.
    Android backups are treated as a single virtual partition containing all files.
    """

    VIRTUAL_PARTITION_SECTOR = 0
    PBKDF2_KEY_SIZE = 32

    def __init__(self, path_to_backup):
        """
        Initialize the Android backup accessor.

        Args:
            path_to_backup: Path to the .ab backup file

        Raises:
            AndroidBackupError: If the backup cannot be accessed or password is missing
                               for encrypted backups
        """
        if not os.path.isfile(path_to_backup):
            raise AndroidBackupError(f"Android backup path is not a file: {path_to_backup}")

        self.path_to_backup = os.path.abspath(path_to_backup)
        self.path_to_image = self.path_to_backup
        self._password = None

        # Parse header and get decompressed tar data
        self._header = {}
        self._tar_data = None
        self._tar_handle = None
        self._member_lookup = {}

        self._parse_backup()

        # File list cache
        self.list_of_files = None
        self.list_of_dir_inodes = []

        logging.info(f"Android backup accessor initialized for: {path_to_backup}")

    def _parse_backup(self):
        """Parse the Android backup file header and decompress the payload."""
        with open(self.path_to_backup, 'rb') as f:
            # Line 1: Magic string
            magic = f.readline()
            if magic != b'ANDROID BACKUP\n':
                raise AndroidBackupError(f"Invalid Android backup: expected 'ANDROID BACKUP', got {magic!r}")

            # Line 2: Format version
            self._header['format_version'] = int(f.readline().strip())

            # Line 3: Compression flag
            self._header['compression'] = int(f.readline().strip())

            # Line 4: Encryption type
            self._header['encryption'] = f.readline().decode('utf-8').strip()

            logging.info(f"Android backup: version={self._header['format_version']}, "
                        f"compression={self._header['compression']}, "
                        f"encryption={self._header['encryption']}")

            if self._header['encryption'] == 'AES-256':
                self._parse_encrypted_header(f)
                self._password = self._load_password()
                if self._password is None:
                    raise AndroidBackupError(
                        f"Encrypted backup requires password.txt in backup directory or parent. "
                        f"Backup: {self.path_to_backup}"
                    )
                encrypted_data = f.read()
                compressed_data = self._decrypt_payload(encrypted_data)
            elif self._header['encryption'] == 'none':
                compressed_data = f.read()
            else:
                raise AndroidBackupError(f"Unknown encryption type: {self._header['encryption']}")

            # Decompress if compression flag is set
            if self._header['compression'] == 1:
                try:
                    self._tar_data = zlib.decompress(compressed_data)
                except zlib.error as e:
                    raise AndroidBackupError(f"Failed to decompress backup: {e}")
            else:
                self._tar_data = compressed_data

            # Open the tar data as a file-like object
            tar_stream = io.BytesIO(self._tar_data)
            try:
                self._tar_handle = tarfile.open(fileobj=tar_stream, mode='r:')
                self._member_lookup = {m.name: m for m in self._tar_handle.getmembers()}
            except tarfile.TarError as e:
                raise AndroidBackupError(f"Failed to parse tar data: {e}")

    def _parse_encrypted_header(self, f):
        """Parse the additional header lines for encrypted backups."""
        self._header['user_salt'] = bytes.fromhex(f.readline().decode('utf-8').strip())
        self._header['checksum_salt'] = bytes.fromhex(f.readline().decode('utf-8').strip())
        self._header['pbkdf2_rounds'] = int(f.readline().strip())
        self._header['user_iv'] = bytes.fromhex(f.readline().decode('utf-8').strip())
        self._header['master_key_blob'] = bytes.fromhex(f.readline().decode('utf-8').strip())

        logging.info(f"Encrypted backup: PBKDF2 rounds={self._header['pbkdf2_rounds']}")

    def _load_password(self):
        """
        Load password from password.txt file.

        Looks for password.txt in:
        1. Same directory as the .ab file
        2. Parent directory

        Returns:
            Password string or None if not found
        """
        # Check same directory as .ab file
        backup_dir = os.path.dirname(self.path_to_backup)
        password_file = os.path.join(backup_dir, 'password.txt')
        if os.path.exists(password_file):
            return self._read_password_file(password_file)

        # Check parent directory
        parent_dir = os.path.dirname(backup_dir)
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
            logging.info(f"Loaded password from: {path}")
            return password
        except Exception as e:
            logging.error(f"Error reading password file {path}: {e}")
            return None

    def _decrypt_payload(self, encrypted_data):
        """
        Decrypt the encrypted backup payload.

        Requires the pyaes library for AES decryption.
        """
        try:
            import pyaes
        except ImportError:
            raise AndroidBackupError("pyaes library required for encrypted backups. Install with: pip install pyaes")

        # Generate user key from password using PBKDF2
        user_key = hashlib.pbkdf2_hmac(
            'sha1',
            self._password.encode('utf-8'),
            self._header['user_salt'],
            self._header['pbkdf2_rounds'],
            self.PBKDF2_KEY_SIZE
        )

        # Decrypt the master key blob
        master_key_blob = self._header['master_key_blob']
        user_iv = self._header['user_iv']

        aes = pyaes.AESModeOfOperationCBC(user_key, user_iv)
        decrypted_blob = b''
        offset = 0
        while offset < len(master_key_blob):
            decrypted_blob += aes.decrypt(master_key_blob[offset:offset + 16])
            offset += 16

        # Parse the decrypted master key blob
        blob = io.BytesIO(decrypted_blob)
        master_iv_length = blob.read(1)[0]
        master_iv = blob.read(master_iv_length)
        master_key_length = blob.read(1)[0]
        master_key = blob.read(master_key_length)
        master_checksum_length = blob.read(1)[0]
        master_checksum = blob.read(master_checksum_length)

        # Verify checksum (for format version >= 2)
        if self._header['format_version'] >= 2:
            converted_key = self._convert_to_utf8_bytes(master_key)
        else:
            converted_key = master_key

        expected_checksum = hashlib.pbkdf2_hmac(
            'sha1',
            converted_key,
            self._header['checksum_salt'],
            self._header['pbkdf2_rounds'],
            self.PBKDF2_KEY_SIZE
        )

        if master_checksum != expected_checksum:
            raise AndroidBackupError("Invalid password or corrupted backup")

        # Decrypt the payload using the master key
        decrypter = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(master_key, master_iv))
        decrypted_data = decrypter.feed(encrypted_data) + decrypter.feed()

        return decrypted_data

    def _convert_to_utf8_bytes(self, input_bytes):
        """Convert bytes to UTF-8 byte array format (for checksum verification in v2+ backups)."""
        output = []
        for byte in input_bytes:
            if byte < 0x80:
                output.append(byte)
            else:
                output.append(0xef | (byte >> 12))
                output.append(0xbc | ((byte >> 6) & 0x3f))
                output.append(0x80 | (byte & 0x3f))
        return bytes(output)

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

        Android backups are treated as a single virtual partition.
        """
        partition = PartitionItem(
            start=self.VIRTUAL_PARTITION_SECTOR,
            end=self.VIRTUAL_PARTITION_SECTOR,
            partition_type='Android Backup',
            allocated=True
        )
        partition.files = self.files
        return [partition]

    def _normalize_path(self, path):
        """
        Normalize a tar member path to always have a leading slash.
        """
        path = path.lstrip('./')
        if not path.startswith('/'):
            path = '/' + path
        return path

    def _populate_file_list(self):
        """Populate the list of files from the backup."""
        try:
            inode_counter = 0

            for member in self._member_lookup.values():
                # Skip directories
                if not member.isfile():
                    continue

                full_path = self._normalize_path(member.name)

                file_item = AndroidBackupFileItem(
                    full_path=full_path,
                    inode=inode_counter,
                    file_size=member.size,
                    partition_sector=self.VIRTUAL_PARTITION_SECTOR,
                    tar_member_name=member.name,
                    backup_accessor=self
                )

                file_item.timestamps['m_time'] = member.mtime
                file_item.timestamps['a_time'] = None
                file_item.timestamps['cr_time'] = None
                file_item.path_to_disk_image = self.path_to_backup

                self.list_of_files.append(file_item)
                inode_counter += 1

            logging.info(f"Populated {len(self.list_of_files)} files from Android backup")

        except Exception as e:
            logging.error(f"Error populating file list from Android backup: {e}")
            raise AndroidBackupError(f"Failed to read Android backup: {e}")

    def _read_file_content(self, file_item):
        """
        Read file content from the backup.

        Args:
            file_item: AndroidBackupFileItem to read

        Returns:
            File content as bytes
        """
        try:
            member = self._member_lookup.get(file_item._tar_member_name)
            if member is None:
                logging.warning(f"Member not found in backup: {file_item._tar_member_name}")
                return b''

            file_obj = self._tar_handle.extractfile(member)
            if file_obj is not None:
                data = file_obj.read()
                file_obj.close()
                return data
            else:
                logging.warning(f"Could not extract file: {file_item.full_path}")
                return b''

        except Exception as e:
            logging.error(f"Error reading file {file_item.full_path} from backup: {e}")
            return b''

    def get_file_system_handles(self):
        """Return a dictionary of file system handles."""
        return {self.VIRTUAL_PARTITION_SECTOR: self}

    def close(self):
        """Close handles and free memory."""
        if self._tar_handle is not None:
            self._tar_handle.close()
            self._tar_handle = None
        self._tar_data = None
        self._member_lookup = {}

    def __del__(self):
        """Cleanup when the accessor is garbage collected."""
        self.close()

    def get_list_of_files(self, list_of_files):
        """Compatibility method for GenericDiskAccessor interface."""
        self.list_of_files = list_of_files
        self._populate_file_list()
        return self.list_of_files

    def get_media_size(self):
        """Return total size of all files in the backup."""
        return sum(f.file_size for f in self.files)


def is_android_backup(path):
    """
    Check if a given path is an Android backup file.

    Args:
        path: Path to check

    Returns:
        True if the path appears to be an Android backup, False otherwise
    """
    if not os.path.isfile(path):
        return False

    # Check by extension
    lower_path = path.lower()
    if not lower_path.endswith('.ab'):
        return False

    # Verify magic bytes
    try:
        with open(path, 'rb') as f:
            magic = f.readline()
            return magic == b'ANDROID BACKUP\n'
    except (IOError, OSError):
        return False
