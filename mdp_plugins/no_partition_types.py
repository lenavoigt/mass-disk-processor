from typing import Dict, Optional

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin

# corresponds to pytsk3.TSK_FS_TYPE_ENUM... this should probably be elsewhere
TSK_FS_TYPE_REVERSE = {
    1: 'ntfs',
    2: 'fat12',
    4: 'fat16',
    8: 'fat32',
    10: 'exfat',
    16: 'ffs1',
    32: 'ffs1b',
    64: 'ffs2',
    128: 'ext2',
    256: 'ext3',
    8192: 'ext4',
    512: 'swap',
    1024: 'raw',
    2048: 'iso9660',
    4096: 'hfs',
    65536: 'apfs',
    131072: 'logical',
    16384: 'yaffs2',
    4294967295: 'unsupported'
}


class NumberOfPartitionTypes(MDPPlugin):
    name = 'no_partition_types'
    description = 'Number of partitions of different fs types'
    expected_results = [f'fs_type_count_{fs_name}' for fs_name in set(TSK_FS_TYPE_REVERSE.values())]

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor

        partitions = None
        # fs that will be counted correspond to tsk fs types
        fs_type_counts: Dict[str, Optional[int]] = {
            f'fs_type_count_{fs_name}': None
            for fs_name in set(TSK_FS_TYPE_REVERSE.values())
        }

        try:
            partitions = disk_image.partitions
        except Exception as e:
            print(e)

        if partitions:
            # If partition table exists, count for each type is set to 0
            for key in fs_type_counts:
                fs_type_counts[key] = 0

            for partition in partitions:
                try:
                    fs_handle = disk_image._try_getting_file_system_handle(offset=partition.start_sector * 512) # using default sector size here...
                    if fs_handle:
                        fs_type_enum = fs_handle.info.ftype
                        fs_type = TSK_FS_TYPE_REVERSE.get(fs_type_enum, 'unknown')
                        key = f'fs_type_count_{fs_type}'
                        if key in fs_type_counts:
                            fs_type_counts[key] += 1
                    else:
                        # dont count this as unknown fs as might be misaligned or non-data part
                        continue
                except Exception as e:
                    # print(f"Error reading FS on partition at sector {partition.start}: {e}")
                    continue

        result = self.create_result(target_disk_image)
        self.set_results(result, fs_type_counts)
        return result
