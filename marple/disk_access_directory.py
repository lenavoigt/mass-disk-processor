"""
Directory Accessor for Marple

Provides access to raw directories as if they were disk images/filesystems.
Uses os.walk() to enumerate files and os.stat() for file metadata.
"""

import os
import logging

from marple.file_object import FileItem
from marple.partition_object import PartitionItem


class DirectoryAccessorError(Exception):
    """Exception raised for directory access errors."""
    pass


class DirectoryFileItem(FileItem):
    """
    Extended FileItem for files within directories.

    Handles reading file content directly from the filesystem.
    """

    def __init__(self, full_path, inode, file_size, partition_sector, absolute_path, directory_accessor):
        super().__init__(full_path, inode, file_size, partition_sector)
        self._absolute_path = absolute_path  # Full path on disk
        self._directory_accessor = directory_accessor
        self._cached_data = None

    def read(self, size_to_read=None, fs_handle=None):
        """
        Read data from the file on disk.

        For directories, fs_handle is ignored - we read directly from the filesystem.
        """
        if self.file_size == 0:
            return b''

        # Load full file content if not cached
        if self._cached_data is None:
            self._cached_data = self._directory_accessor._read_file_content(self)
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


class DirectoryAccessor:
    """
    Accessor for raw directories that provides a similar interface to GenericDiskAccessor.

    Directories are treated as a single virtual partition containing all files.
    """

    VIRTUAL_PARTITION_SECTOR = 0

    def __init__(self, path_to_directory):
        """
        Initialize the directory accessor.

        Args:
            path_to_directory: Path to the directory

        Raises:
            DirectoryAccessorError: If the directory cannot be accessed
        """
        if not os.path.isdir(path_to_directory):
            raise DirectoryAccessorError(f"Path is not a directory: {path_to_directory}")

        self.path_to_directory = os.path.abspath(path_to_directory)
        self.path_to_image = self.path_to_directory  # Compatibility alias

        # File list cache
        self.list_of_files = None
        self.list_of_dir_inodes = []

        logging.info(f"Directory accessor initialized for: {path_to_directory}")

    @property
    def files(self):
        """Return list of FileItem objects for all files in the directory."""
        if self.list_of_files is None:
            self.list_of_files = []
            self._populate_file_list()
        return self.list_of_files

    @property
    def partitions(self):
        """
        Return list of partition objects.

        Directories are treated as a single virtual partition.
        """
        partition = PartitionItem(
            start=self.VIRTUAL_PARTITION_SECTOR,
            end=self.VIRTUAL_PARTITION_SECTOR,
            partition_type='Directory',
            allocated=True
        )
        partition.files = self.files
        return [partition]

    def _get_relative_path(self, absolute_path):
        """
        Convert absolute path to relative path with leading slash.

        Args:
            absolute_path: Full path on disk

        Returns:
            Path relative to the base directory with leading slash
        """
        rel_path = os.path.relpath(absolute_path, self.path_to_directory)
        # Normalize to forward slashes and add leading slash
        rel_path = '/' + rel_path.replace(os.sep, '/')
        return rel_path

    def _populate_file_list(self):
        """Populate the list of files from the directory."""
        try:
            inode_counter = 0

            for root, dirs, files in os.walk(self.path_to_directory):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for filename in files:
                    # Skip hidden files
                    if filename.startswith('.'):
                        continue

                    absolute_path = os.path.join(root, filename)

                    # Skip if not a regular file (e.g., symlinks, special files)
                    if not os.path.isfile(absolute_path):
                        continue

                    try:
                        stat_info = os.stat(absolute_path)
                    except (OSError, IOError) as e:
                        logging.warning(f"Could not stat file {absolute_path}: {e}")
                        continue

                    full_path = self._get_relative_path(absolute_path)

                    file_item = DirectoryFileItem(
                        full_path=full_path,
                        inode=inode_counter,
                        file_size=stat_info.st_size,
                        partition_sector=self.VIRTUAL_PARTITION_SECTOR,
                        absolute_path=absolute_path,
                        directory_accessor=self
                    )

                    # Set timestamps from stat
                    # Note: m_time may be preserved from extraction, but cr_time and a_time
                    # reflect local filesystem operations, not original device timestamps
                    file_item.timestamps['m_time'] = stat_info.st_mtime
                    file_item.timestamps['a_time'] = None
                    file_item.timestamps['cr_time'] = None

                    file_item.path_to_disk_image = self.path_to_directory

                    self.list_of_files.append(file_item)
                    inode_counter += 1

            logging.info(f"Populated {len(self.list_of_files)} files from directory")

        except Exception as e:
            logging.error(f"Error populating file list from directory: {e}")
            raise DirectoryAccessorError(f"Failed to read directory: {e}")

    def _read_file_content(self, file_item):
        """
        Read file content from the filesystem.

        Args:
            file_item: DirectoryFileItem to read

        Returns:
            File content as bytes
        """
        try:
            with open(file_item._absolute_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logging.error(f"Error reading file {file_item._absolute_path}: {e}")
            return b''

    def get_file_system_handles(self):
        """Return a dictionary of file system handles."""
        return {self.VIRTUAL_PARTITION_SECTOR: self}

    def close(self):
        """Close the accessor (no-op for directories)."""
        pass

    def __del__(self):
        """Cleanup when the accessor is garbage collected."""
        self.close()

    def get_list_of_files(self, list_of_files):
        """Compatibility method for GenericDiskAccessor interface."""
        self.list_of_files = list_of_files
        self._populate_file_list()
        return self.list_of_files

    def get_media_size(self):
        """Return total size of all files in the directory."""
        return sum(f.file_size for f in self.files)


def is_raw_directory(path):
    """
    Check if a given path is a raw directory (not an iOS backup or other special format).

    Args:
        path: Path to check

    Returns:
        True if the path is a plain directory, False otherwise
    """
    if not os.path.isdir(path):
        return False

    # Import here to avoid circular imports
    from marple.disk_access_ios_backup import is_ios_backup

    # Exclude iOS backups - they have their own accessor
    if is_ios_backup(path):
        return False

    return True
