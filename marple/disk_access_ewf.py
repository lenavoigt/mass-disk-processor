import logging
import os
import pytsk3
import pyewf


from marple.file_object import FileItem
from marple.disk_access_raw import DiskAccessorError
from marple.disk_access_generic import GenericDiskAccessor
from marple.partition_object import PartitionItem

class EwfDiskAccessor(GenericDiskAccessor):

    def __init__(self, path_to_disk_image):
        if type(path_to_disk_image) is not str:
            raise TypeError("path_to_disk_image should be a string, not {}".format(type(path_to_disk_image)))
        if not os.path.exists(path_to_disk_image):
            raise FileNotFoundError("Disk image '{}' not found".format(path_to_disk_image))

        f = open(path_to_disk_image, 'rb')
        sector = f.read(512)
        if sector[0:3] != b'EVF':
            raise DiskAccessorError('Not an EWF disk image')
        f.close()
        self.path_to_image = path_to_disk_image
        self.list_of_files = None
        self.list_of_folders = None
        self.list_of_dir_inodes = None

        # open all the file parts once
        image_paths = self.get_all_parts_of_potentially_split_ewf()
        self.file_object_paths = []
        for each in image_paths:
            file_object = open(each, "rb")
            self.file_object_paths.append(file_object)


    @property
    def list_of_file_names(self):
        out = []
        for each in self.list_of_files:
            out.append(each.full_path)
        return out

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
                a = PartitionItem(each_partition.start,
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

        if fs_handle:  # we just have a file system at this point, no partitions
            logging.info("File system found in root of image")
            self._get_list_of_files_from_volume(fs_handle)
            # adds image path to all files
            for each in list_of_files:
                each.path_to_disk_image = self.path_to_image
                #each.fs_handle = fs_handle[each.partition_sector]

        else:
            logging.info("No file system found in root of image")
            self._get_list_of_files_from_all_partitions()  # TODO may need to pass sector size here for 4k sectors

        # adds image path to all files
        for each in list_of_files:
            each.path_to_disk_image = self.path_to_image


        return self.list_of_files


    def get_all_parts_of_potentially_split_ewf(self):
        return pyewf.glob(self.path_to_image)



    def get_disk_image_sector(self, sector_number, sector_size=512):
        ewf_handle = pyewf.handle()
        ewf_handle.open_file_objects(self.file_object_paths)
        img = ewf_Img_Info(ewf_handle)
        data = img.read(512*sector_number, sector_size)
        img.close()
        ewf_handle.close()
        return data

    def get_partition_sector(self, partiton_sector_offset, sector_number, sector_size=512):
        ewf_handle = pyewf.handle()
        ewf_handle.open_file_objects(self.file_object_paths)
        img = ewf_Img_Info(ewf_handle)
        data = img.read(sector_size*partiton_sector_offset + sector_size*sector_number, sector_size)
        img.close()
        ewf_handle.close()
        return data


    def get_partition_block(self, partiton_sector_offset, block_number, block_size, sector_size=512):
        logging.warning('Block size on FAT =sector size due to pytsk')
        ewf_handle = pyewf.handle()
        ewf_handle.open_file_objects(self.file_object_paths)
        img = ewf_Img_Info(ewf_handle)
        data = img.read(sector_size * partiton_sector_offset + block_size * block_number, block_size)
        img.close()
        ewf_handle.close()
        return data



    """Return list of partitions in disk image"""
    def _get_partitions(self):
        ewf_handle = pyewf.handle()
        ewf_handle.open_file_objects(self.file_object_paths)
        img = ewf_Img_Info(ewf_handle)
        partition_table = pytsk3.Volume_Info(img)
        img.close()
        ewf_handle.close()
        return partition_table


    """Attempt to get a file system handle at specified offset"""
    def _try_getting_file_system_handle(self, offset):
        ewf_handle = pyewf.handle()
        ewf_handle.open_file_objects(self.file_object_paths)
        img = ewf_Img_Info(ewf_handle)

        try:
            # get a handle to the file system
            return pytsk3.FS_Info(img, offset=offset)
        except OSError:
            return None


    def __del__(self):
        for each in self.file_object_paths:
            each.close()

    def get_media_size(self):
        ewf_handle = pyewf.handle()
        ewf_handle.open_file_objects(self.file_object_paths)
        img = ewf_Img_Info(ewf_handle)
        disk_size_bytes = img.get_size()
        return disk_size_bytes

class ewf_Img_Info(pytsk3.Img_Info):
    def __init__(self, ewf_handle):
        self._ewf_handle = ewf_handle
        super(ewf_Img_Info, self).__init__(
            url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

    def close(self):
        self._ewf_handle.close()

    def read(self, offset, size):
        self._ewf_handle.seek(offset)
        return self._ewf_handle.read(size)

    def get_size(self):
        return self._ewf_handle.get_media_size()