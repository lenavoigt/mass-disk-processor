import logging
import os
import math
import pytsk3
from marple.file_object import FileItem
class DiskAccessorError(Exception):
    pass

class GenericDiskAccessor(object):

    """Generate list of files on partition starting at supplied dir"""
    def _populate_file_list(self, starting_dir_object, parent_path, partition_sector):
        if starting_dir_object is None:
            return

        logging.info('Folder is {}'.format(parent_path))

        self.list_of_dir_inodes.append(starting_dir_object.info.addr)

        # logging.debug('Processing {}'.format(starting_dir_object.info.names.name))
        for each_file in starting_dir_object:
            filename_decoded = each_file.info.name.name.decode('UTF-8', 'replace')
            full_path = os.path.join(parent_path, filename_decoded)
            if each_file.info.meta is None:
                logging.debug("{} has no metadata".format(full_path))
                continue

            # print(each_file.info.name.name, each_file.info.meta.type, each_file.info.meta.flags, each_file.info.meta.mode)
            # added this in trying to identify volume label entry on fat root entry

            if each_file.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG:
                # is a file
                a_file = FileItem(full_path,
                                  each_file.info.meta.addr,
                                  each_file.info.meta.size,
                                  partition_sector)
                a_file.timestamps['cr_time'] = each_file.info.meta.crtime
                a_file.timestamps['m_time'] = each_file.info.meta.mtime
                a_file.timestamps['a_time'] = each_file.info.meta.atime
                a_file.status = each_file.info.meta.type
                self.list_of_files.append(a_file)

                #logging.debug('Added {}'.format(full_path))


            elif each_file.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
                # is a directory
                # logging.debug(each_file.info.name.name)
                if each_file.info.name.name == b'.' or each_file.info.name.name == b'..':
                    pass
                elif each_file.info.name.name == b'$OrphanFiles':
                    logging.debug("skipped $OrphanFiles for now".format())
                else: # is proper dir
                    if each_file.info.meta.addr not in self.list_of_dir_inodes:
                        try:
                            # has not been processed yet (needed to stop infinite recursion)
                            self._populate_file_list(each_file.as_directory(), full_path, partition_sector)
                        except OSError as e:
                            logging.error("A major error occurred reading {} ({})".format(full_path, e))
                    else:
                        logging.debug("skipped {} as in list of dir inodes".format(each_file.info.meta.addr))

            elif each_file.info.meta.type == pytsk3.TSK_FS_META_TYPE_LNK:
                # deliberately ignoring symbolic links
                pass
            else:
                logging.debug('Unsupported file type: {} {} '.format(each_file.info.name.name,
                                                                          each_file.info.meta.type))



    """NEEDS IMPLEMENTING IN SUBCLASS"""
    def _get_partitions(self):
        raise NotImplementedError('Needs implementing in subclass')

    """NEEDS IMPLEMENTING IN SUBCLASS"""
    def _try_getting_file_system_handle(self, offset):
        raise NotImplementedError('Needs implementing in subclass')

    """Populate list of files for a disk image of a volume only"""
    def _get_list_of_files_from_volume(self, fs_handle):
        self.list_of_dir_inodes = []
        root_directory_object = fs_handle.open_dir('/', 0)
        self._populate_file_list(root_directory_object, 'P_0/', 0)
        logging.info('File list populated')

    """Populate list of files for a disk image with partitions"""
    def _get_list_of_files_from_all_partitions(self, sector_size=512):
        partitions = self._get_partitions()
        logging.info("Detected some partitions")

        for i, each_partition in enumerate(partitions):
            logging.info('processing partition: {}'.format(i))
            if each_partition.flags == pytsk3.TSK_VS_PART_FLAG_UNALLOC:
                logging.info("--- needs scanning (photorec/foremost)")
            elif each_partition.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
                logging.info("--- needs processing (fls)")
                fs_handle = self._try_getting_file_system_handle(offset=sector_size * each_partition.start)
                if fs_handle is not None:
                    root_directory_object = fs_handle.open_dir('/', 0)
                    self._populate_file_list(root_directory_object, 'P_{}/'.format(each_partition.start),
                                         each_partition.start)
                    logging.info('File list populated for'.format(each_partition.start))
                else:
                    print('TSK unsupported fs found at {}'.format(each_partition.start))
            elif each_partition.flags == pytsk3.TSK_VS_PART_FLAG_META:
                # ignoring meta volumes on purpose
                pass
            else:
                logging.warning('Partition type not identified {}'.format(each_partition.flags))


    """Return a dictionary of file system handles"""
    def get_file_system_handles(self):
        handles = {}

        fs_handle = self._try_getting_file_system_handle(offset=0)
        if fs_handle:  # we just have a file system at this point, no partitions
            handles[0] = fs_handle
        else:
            partitions = self._get_partitions()
            for each_partition in partitions:
                if each_partition.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
                    fs_handle = self._try_getting_file_system_handle(offset=512 * each_partition.start)
                    handles[each_partition.start] = fs_handle
        return handles

    """NEEDS IMPLEMENTING IN SUBCLASS"""
    def get_media_size(self):
        raise NotImplementedError('Needs implementing in subclass')

    def get_block_size_of_volume_tsk(self, partition_start_sector, sector_size=512):
        fs_handle = self._try_getting_file_system_handle(offset=partition_start_sector*sector_size)
        if fs_handle:  # we just have a file system at this point, no partitions
            block_size = fs_handle.info.block_size
            return block_size
        else:
            raise Exception('No valid file system at offset {}'.format(partition_start_sector))


    def get_block_count_of_volume_tsk(self, partition_start_sector, sector_size=512):
        fs_handle = self._try_getting_file_system_handle(offset=partition_start_sector*sector_size)
        if fs_handle:  # we just have a file system at this point, no partitions
            block_count = fs_handle.info.block_count
            return block_count
        else:
            raise Exception('No valid file system at offset {}'.format(partition_start_sector))




    def get_fat_info_manually(self, partition_start_sector, sector_size=512):
        fs_handle = self._try_getting_file_system_handle(offset=partition_start_sector*sector_size)
        if fs_handle:  # we just have a file system at this point, no partitions
            vbr = self.get_partition_block(partition_start_sector, 0, sector_size)

            # 82 for FAT32, 54 for FAT16
            fs_type1 = vbr[54:54+5]
            fs_type2 = vbr[82:82 + 5]

            #TODO look into these positiosn properly
            if fs_type1 == b'FAT12' or fs_type2 == b'FAT12':
                sectors_per_fat = int.from_bytes(vbr[22:23], 'little', signed=False)
                fs_type = fs_type1
            elif fs_type1 == b'FAT16' or fs_type2 == b'FAT16':
                sectors_per_fat = int.from_bytes(vbr[22:23], 'little', signed=False)
                fs_type = fs_type1
            elif fs_type1 == b'FAT32' or fs_type2 == b'FAT32':
                sectors_per_fat = int.from_bytes(vbr[36:40], 'little', signed=False)
                fs_type = fs_type2
            else:
                raise NotImplementedError('FAT info requested for file system "{}"'.format(fs_type))

            sectors_per_cluster = int.from_bytes(vbr[13:14], 'little', signed=False)
            reserved_sectors = int.from_bytes(vbr[14:16], 'little', signed=False)
            copies_of_fat = int.from_bytes(vbr[16:17], 'little', signed=False)

            total_sectors_small = int.from_bytes(vbr[19:21], 'little', signed=False)

            total_sectors = int.from_bytes(vbr[32:36], 'little', signed=False)


            return {'sectors_per_cluster': sectors_per_cluster,
                    'reserved_sectors': reserved_sectors,
                    'copies_of_fat': copies_of_fat,
                    'sectors_per_fat': sectors_per_fat,
                    'total_sectors': total_sectors,
                    'fs_type': fs_type
                    }
        else:
            raise Exception('No valid file system at offset {}'.format(partition_start_sector))


    def get_fs_type_directly(self, partition_start_sector, sector_size=512):
        info = self.get_fat_info_manually(partition_start_sector, sector_size)
        return info['fs_type']

    def get_block_size_of_fat_volume(self, partition_start_sector, sector_size=512):
        info = self.get_fat_info_manually(partition_start_sector, sector_size)
        return info['sectors_per_cluster'] * sector_size

    def get_block_count_of_fat_volume(self, partition_start_sector, sector_size=512):
        info = self.get_fat_info_manually(partition_start_sector, sector_size)
        data_area_sector_total = info['total_sectors'] - self.get_data_area_start_sector_of_fat_volume(partition_start_sector, sector_size)
        data_area_cluster_total = data_area_sector_total / info['sectors_per_cluster']
        return math.ceil(data_area_cluster_total)

    def get_data_area_start_sector_of_fat_volume(self, partition_start_sector, sector_size=512):
        info = self.get_fat_info_manually(partition_start_sector, sector_size)
        return info['reserved_sectors'] + (info['copies_of_fat'] * info['sectors_per_fat'])

    def get_cluster_no_from_sector(self, partition_start_sector, sector_size=512):
        raise NotImplementedError