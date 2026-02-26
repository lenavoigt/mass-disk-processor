"""
Tar Archive Accessor for Marple

Provides access to tar archives as if they were disk images/filesystems.
Uses Python's tarfile module for streaming access without extracting to temp files.
"""

import os
import logging
import tarfile

from marple.file_object import FileItem
from marple.partition_object import PartitionItem


class TarAccessorError(Exception):
    """Exception raised for tar archive access errors."""
    pass


class TarFileItem(FileItem):
    """
    Extended FileItem for files within tar archives.

    Handles reading file content directly from the tar archive without
    extracting to temporary files.
    """

    def __init__(self, full_path, inode, file_size, partition_sector, tar_member_name, tar_accessor):
        super().__init__(full_path, inode, file_size, partition_sector)
        self._tar_member_name = tar_member_name  # Original name in tar archive
        self._tar_accessor = tar_accessor        # Reference to parent accessor
        self._cached_data = None                 # Cache for file content

    def read(self, size_to_read=None, fs_handle=None):
        """
        Read data from the tar archive file.

        For tar archives, fs_handle is ignored - we use the tar accessor instead.
        """
        if self.file_size == 0:
            return b''

        # Load full file content if not cached
        if self._cached_data is None:
            self._cached_data = self._tar_accessor._read_file_content(self)
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


class TarAccessor:
    """
    Accessor for tar archives that provides a similar interface to GenericDiskAccessor.

    Tar archives are treated as a single virtual partition containing all files
    with their original path structure.
    """

    # Virtual partition sector for tar archives
    VIRTUAL_PARTITION_SECTOR = 0

    def __init__(self, path_to_tar):
        """
        Initialize the tar archive accessor.

        Args:
            path_to_tar: Path to the tar archive file

        Raises:
            TarAccessorError: If the tar archive cannot be accessed
        """
        if not os.path.isfile(path_to_tar):
            raise TarAccessorError(f"Tar archive path is not a file: {path_to_tar}")

        self.path_to_tar = os.path.abspath(path_to_tar)
        self.path_to_image = self.path_to_tar  # Compatibility alias

        # Verify it's a valid tar file
        if not tarfile.is_tarfile(path_to_tar):
            raise TarAccessorError(f"Not a valid tar archive: {path_to_tar}")

        # Keep the tar file open for efficient access
        self._tar_handle = tarfile.open(self.path_to_tar, 'r:*')

        # Build a lookup table of tar members by name for fast access
        self._member_lookup = {m.name: m for m in self._tar_handle.getmembers()}

        # File list cache
        self.list_of_files = None
        self.list_of_dir_inodes = []

        logging.info(f"Tar archive accessor initialized for: {path_to_tar}")

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

        Tar archives are treated as a single virtual partition.
        """
        partition = PartitionItem(
            start=self.VIRTUAL_PARTITION_SECTOR,
            end=self.VIRTUAL_PARTITION_SECTOR,
            partition_type='Tar Archive',
            allocated=True
        )
        partition.files = self.files
        return [partition]

    def _normalize_path(self, path):
        """
        Normalize a tar member path to always have a leading slash.

        Args:
            path: The original path from the tar archive

        Returns:
            Normalized path with leading slash
        """
        # Remove any leading ./ or ./
        path = path.lstrip('./')

        # Ensure leading slash
        if not path.startswith('/'):
            path = '/' + path

        return path

    def _populate_file_list(self):
        """Populate the list of files from the tar archive."""
        try:
            inode_counter = 0

            for member in self._member_lookup.values():
                # Skip directories, only process regular files
                if not member.isfile():
                    continue

                # Normalize the path
                full_path = self._normalize_path(member.name)

                # Create FileItem
                file_item = TarFileItem(
                    full_path=full_path,
                    inode=inode_counter,
                    file_size=member.size,
                    partition_sector=self.VIRTUAL_PARTITION_SECTOR,
                    tar_member_name=member.name,
                    tar_accessor=self
                )

                # Set modification time from tar member
                file_item.timestamps['m_time'] = member.mtime
                file_item.timestamps['a_time'] = None
                file_item.timestamps['cr_time'] = None

                file_item.path_to_disk_image = self.path_to_tar

                self.list_of_files.append(file_item)
                inode_counter += 1

            logging.info(f"Populated {len(self.list_of_files)} files from tar archive")

        except Exception as e:
            logging.error(f"Error populating file list from tar: {e}")
            raise TarAccessorError(f"Failed to read tar archive: {e}")

    def _read_file_content(self, file_item):
        """
        Read file content from the tar archive.

        Args:
            file_item: TarFileItem to read

        Returns:
            File content as bytes
        """
        try:
            member = self._member_lookup.get(file_item._tar_member_name)
            if member is None:
                logging.warning(f"Member not found in tar: {file_item._tar_member_name}")
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
            logging.error(f"Error reading file {file_item.full_path} from tar: {e}")
            return b''

    def get_file_system_handles(self):
        """
        Return a dictionary of file system handles.

        For tar archives, we return a dict with a reference to self,
        though FileItem.read() handles file access directly via the
        persistent tar handle.
        """
        return {self.VIRTUAL_PARTITION_SECTOR: self}

    def close(self):
        """Close the tar archive handle."""
        if self._tar_handle is not None:
            self._tar_handle.close()
            self._tar_handle = None

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


def is_tar_archive(path):
    """
    Check if a given path is a tar archive.

    Args:
        path: Path to check

    Returns:
        True if the path appears to be a tar archive, False otherwise
    """
    if not os.path.isfile(path):
        return False

    # Check by extension
    lower_path = path.lower()
    tar_extensions = ('.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz')

    return any(lower_path.endswith(ext) for ext in tar_extensions)
