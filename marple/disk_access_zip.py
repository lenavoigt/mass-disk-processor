"""
Zip Archive Accessor for Marple

Provides access to zip archives as if they were disk images/filesystems.
Uses Python's zipfile module for direct access without extracting to temp files.
"""

import os
import logging
import zipfile
from datetime import datetime

from marple.file_object import FileItem
from marple.partition_object import PartitionItem


class ZipAccessorError(Exception):
    """Exception raised for zip archive access errors."""
    pass


class ZipFileItem(FileItem):
    """
    Extended FileItem for files within zip archives.

    Handles reading file content directly from the zip archive without
    extracting to temporary files.
    """

    def __init__(self, full_path, inode, file_size, partition_sector, zip_member_name, zip_accessor):
        super().__init__(full_path, inode, file_size, partition_sector)
        self._zip_member_name = zip_member_name  # Original name in zip archive
        self._zip_accessor = zip_accessor        # Reference to parent accessor
        self._cached_data = None                 # Cache for file content

    def read(self, size_to_read=None, fs_handle=None):
        """
        Read data from the zip archive file.

        For zip archives, fs_handle is ignored - we use the zip accessor instead.
        """
        if self.file_size == 0:
            return b''

        # Load full file content if not cached
        if self._cached_data is None:
            self._cached_data = self._zip_accessor._read_file_content(self)
            self._FileItem__bytes_read = 0  # Reset read position

        if self._cached_data is None:
            return b''

        if size_to_read is None:
            # Return all data
            return self._cached_data
        else:
            # Sequential read support
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


class ZipAccessor:
    """
    Accessor for zip archives that provides a similar interface to GenericDiskAccessor.

    Zip archives are treated as a single virtual partition containing all files
    with their original path structure.
    """

    # Virtual partition sector for zip archives
    VIRTUAL_PARTITION_SECTOR = 0

    def __init__(self, path_to_zip):
        """
        Initialize the zip archive accessor.

        Args:
            path_to_zip: Path to the zip archive file

        Raises:
            ZipAccessorError: If the zip archive cannot be accessed
        """
        if not os.path.isfile(path_to_zip):
            raise ZipAccessorError(f"Zip archive path is not a file: {path_to_zip}")

        self.path_to_zip = os.path.abspath(path_to_zip)
        self.path_to_image = self.path_to_zip  # Compatibility alias

        # Verify it's a valid zip file
        if not zipfile.is_zipfile(path_to_zip):
            raise ZipAccessorError(f"Not a valid zip archive: {path_to_zip}")

        # Keep the zip file open for efficient access
        self._zip_handle = zipfile.ZipFile(self.path_to_zip, 'r')

        # Build a lookup table of zip members by name for fast access
        self._member_lookup = {info.filename: info for info in self._zip_handle.infolist()}

        # File list cache
        self.list_of_files = None
        self.list_of_dir_inodes = []

        logging.info(f"Zip archive accessor initialized for: {path_to_zip}")

    @property
    def files(self):
        """Return list of FileItem objects for all files in the archive."""
        if self.list_of_files is None:
            self.list_of_files = []
            self._populate_file_list()
        return self.list_of_files

    @property
    def partitions(self):
        """
        Return list of partition objects.

        Zip archives are treated as a single virtual partition.
        """
        partition = PartitionItem(
            start=self.VIRTUAL_PARTITION_SECTOR,
            end=self.VIRTUAL_PARTITION_SECTOR,
            partition_type='Zip Archive',
            allocated=True
        )
        partition.files = self.files
        return [partition]

    def _normalize_path(self, path):
        """
        Normalize a zip member path to always have a leading slash.

        Args:
            path: The original path from the zip archive

        Returns:
            Normalized path with leading slash
        """
        # Remove any leading ./
        path = path.lstrip('./')

        # Ensure leading slash
        if not path.startswith('/'):
            path = '/' + path

        return path

    def _zipinfo_to_timestamp(self, zip_info):
        """
        Convert ZipInfo date_time tuple to Unix timestamp.

        Args:
            zip_info: ZipInfo object

        Returns:
            Unix timestamp or None if conversion fails
        """
        try:
            # date_time is a tuple: (year, month, day, hour, minute, second)
            dt = datetime(*zip_info.date_time)
            return dt.timestamp()
        except (ValueError, TypeError, OSError):
            return None

    def _populate_file_list(self):
        """Populate the list of files from the zip archive."""
        try:
            inode_counter = 0

            for info in self._member_lookup.values():
                # Skip directories (they end with / in zip files)
                if info.filename.endswith('/'):
                    continue

                # Skip if it's marked as a directory
                if info.is_dir():
                    continue

                # Normalize the path
                full_path = self._normalize_path(info.filename)

                # Create FileItem
                file_item = ZipFileItem(
                    full_path=full_path,
                    inode=inode_counter,
                    file_size=info.file_size,  # Uncompressed size
                    partition_sector=self.VIRTUAL_PARTITION_SECTOR,
                    zip_member_name=info.filename,
                    zip_accessor=self
                )

                # Set modification time from zip member
                file_item.timestamps['m_time'] = self._zipinfo_to_timestamp(info)
                file_item.timestamps['a_time'] = None
                file_item.timestamps['cr_time'] = None

                file_item.path_to_disk_image = self.path_to_zip

                self.list_of_files.append(file_item)
                inode_counter += 1

            logging.info(f"Populated {len(self.list_of_files)} files from zip archive")

        except Exception as e:
            logging.error(f"Error populating file list from zip: {e}")
            raise ZipAccessorError(f"Failed to read zip archive: {e}")

    def _read_file_content(self, file_item):
        """
        Read file content from the zip archive.

        Args:
            file_item: ZipFileItem to read

        Returns:
            File content as bytes
        """
        try:
            info = self._member_lookup.get(file_item._zip_member_name)
            if info is None:
                logging.warning(f"Member not found in zip: {file_item._zip_member_name}")
                return b''

            with self._zip_handle.open(info) as file_obj:
                data = file_obj.read()
                return data

        except Exception as e:
            logging.error(f"Error reading file {file_item.full_path} from zip: {e}")
            return b''

    def get_file_system_handles(self):
        """
        Return a dictionary of file system handles.

        For zip archives, we return a dict with a reference to self,
        though FileItem.read() handles file access directly via the
        persistent zip handle.
        """
        return {self.VIRTUAL_PARTITION_SECTOR: self}

    def close(self):
        """Close the zip archive handle."""
        if self._zip_handle is not None:
            self._zip_handle.close()
            self._zip_handle = None

    def __del__(self):
        """Cleanup when the accessor is garbage collected."""
        self.close()

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
        Return total size of all files in the archive.

        Note: This is the uncompressed size of file contents, not the archive size.
        """
        total_size = sum(f.file_size for f in self.files)
        return total_size


def is_zip_archive(path):
    """
    Check if a given path is a zip archive.

    Args:
        path: Path to check

    Returns:
        True if the path appears to be a zip archive, False otherwise
    """
    if not os.path.isfile(path):
        return False

    # Check by extension
    lower_path = path.lower()
    zip_extensions = ('.zip',)

    return any(lower_path.endswith(ext) for ext in zip_extensions)
