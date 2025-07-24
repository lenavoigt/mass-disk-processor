import os
import logging

import pytsk3
import pyewf

from marple.disk_access_generic import GenericDiskAccessor
from marple import partition_object

class DiskAccessorError(Exception):
    pass

class RawDiskAccessor(GenericDiskAccessor):

    def __init__(self, path_to_image):
        if type(path_to_image) is not str:
            raise TypeError("path_to_image should be a string, not {}".format(type(path_to_image)))
        if not os.path.exists(path_to_image):
            raise FileNotFoundError("Disk image {} not found".format(path_to_image))

        try:
            f = open(path_to_image, 'rb')
            sector = f.read(512)
            f.close()
            if sector[510:512] != b'\x55\xAA':
                print(sector)
                raise DiskAccessorError('Not a disk or partition - no 55 AA found at offset 500')

            self.path_to_image = path_to_image
            self.list_of_files = None
            self.list_of_folders = None
            self.list_of_dir_inodes = None
        except PermissionError:
            raise PermissionError("needs root permissions to access attached media")

    @property
    def files(self):
        if self.list_of_files is None:
            self.list_of_files = []
            self.get_list_of_files(self.list_of_files)
            return self.list_of_files
        else:
            # if already generated, just return the current list
            return self.list_of_files


    @property
    def partitions(self):
        '''returns list of partition objects'''
        res = self._get_partitions()
        parts = []
        for each_partition in res:
            if each_partition.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
                a = partition_object.PartitionItem(each_partition.start,
                                                   each_partition.start + each_partition.len -1,
                                                   each_partition.desc.decode())
                a.files = [x for x in self.files if x.partition_sector == each_partition.start]
                parts.append(a)
        return parts

    """Return a list of file objects"""
    def get_list_of_files(self, list_of_files):
        self.list_of_dir_inodes = []
        self.list_of_folders = []
        self.list_of_files = list_of_files

        # is it a full disk or a volume?
        fs_handle = self._try_getting_file_system_handle(offset=0)

        if fs_handle:   # we just have a file system at this point, no partitions

            self._get_list_of_files_from_volume(fs_handle)

        else:
            self._get_list_of_files_from_all_partitions()

        # adds image path to all files
        for each in list_of_files:
            each.path_to_disk_image = self.path_to_image

        return self.list_of_files


    def get_disk_image_sector(self, sector_number, sector_size=512):
        f = open(self.path_to_image, 'rb')
        f.seek(512*sector_number)
        data = f.read(sector_size)
        f.close()
        return data


    def get_partition_sector(self, partiton_sector_offset, sector_number, sector_size=512):
        f = open(self.path_to_image, 'rb')
        f.seek(sector_size * partiton_sector_offset + sector_size * sector_number)
        data = f.read(sector_size)
        f.close()
        return data

    def get_partition_block(self, partiton_sector_offset, block_number, block_size, sector_size=512):
        logging.warning('Block size on FAT = sector size due to pytsk')

        # if fs = FAT do something differnt.
        # Find



        f = open(self.path_to_image, 'rb')
        f.seek(sector_size * partiton_sector_offset + block_size * block_number)
        data = f.read(block_size)
        f.close()
        return data

    """Return list of partitions in disk image"""
    def _get_partitions(self):
        img = pytsk3.Img_Info(self.path_to_image)
        partition_table = pytsk3.Volume_Info(img)
        return partition_table

    """Attempt to get a file system handle at specified offset"""
    def _try_getting_file_system_handle(self, offset):
        img = pytsk3.Img_Info(self.path_to_image)
        try:
            # get a handle to the file system
            return pytsk3.FS_Info(img, offset=offset)
        except OSError:
            return None

    def get_media_size(self):
        img = pytsk3.Img_Info(self.path_to_image)
        disk_size_bytes = img.get_size()
        return disk_size_bytes