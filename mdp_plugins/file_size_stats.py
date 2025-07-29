import pytsk3

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage
import statistics
import mdp_plugins.disk_size

class FileSizeStats(object):
    name = 'file_sizes'
    description = 'Size of data on drive'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files # this doesn't contain symlinks or anything except files with
                                # "each_file.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG"
                                # in current implementation of generic_disk_accessor
        size_array = []
        total_logical = 0
        total_file_blocks = 0
        seen_inodes = set()
        block_sizes = {}

        for each_file in files:
            if each_file.file_size is not None:
                # Skip unallocated files - this might already be done in current impl of generic_disk_accessor
                if not (each_file.flags & pytsk3.TSK_FS_META_FLAG_ALLOC):
                    continue

                # # Skip system files (like $MFT) - Not sure if this is wanted or not... Not excluding this for now
                # filename = each_file.full_path.split("/")[-1]
                # if filename.startswith("$"):
                #     continue

                # Deduplicate inodes (avoid counting hard links multiple times)
                if each_file.inode in seen_inodes:
                    continue
                seen_inodes.add(each_file.inode)

                size_array.append(each_file.file_size)
                total_logical += each_file.file_size

                part_sec = each_file.partition_sector
                if part_sec not in block_sizes:
                    try:
                        block_sizes[part_sec] = disk_image.get_block_size_of_volume_tsk(part_sec)
                    except Exception:
                        block_sizes[part_sec] = 512

                block_size = block_sizes[part_sec]
                blocks = (each_file.file_size + block_size - 1) // block_size # Round up to next full block
                total_file_blocks += blocks * block_size

        try:
            ds = mdp_plugins.disk_size.DiskSize()
            disk_size = ds.get_disk_size(disk_image)
        except Exception as e:
            print(e)
            disk_size = None

        if disk_size is None:
            disk_usage_by_files = None
            disk_usage_by_file_blocks = None
        else:
            disk_usage_by_files = round(100 * total_logical / disk_size, 2)
            disk_usage_by_file_blocks = round(100 * total_file_blocks / disk_size, 2)

        if size_array:
            mean_size = round(statistics.mean(size_array), 2)
            median_size = statistics.median(size_array)
        else:
            mean_size = None
            median_size = None

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'file_size_total': total_logical,
                       'file_size_total_blocks': total_file_blocks,
                       'file_size_mean': mean_size,
                       'file_size_median': median_size,
                       'disk_usage_by_file_size': disk_usage_by_files,
                       'disk_usage_by_file_size_blocks': disk_usage_by_file_blocks # considers blockpadding...
                       }
        return res
