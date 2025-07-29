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
        files = disk_image.files
        size_array = []
        total = 0

        for each_file in files:
            if each_file.file_size is not None:
                size_array.append(each_file.file_size)
                total += each_file.file_size
            else:
                continue

        try:
            ds = mdp_plugins.disk_size.DiskSize()
            disk_size = ds.get_disk_size(disk_image)
        except Exception as e:
            print(e)
            disk_size = None

        if disk_size is None:
            disk_usage_by_files = None
        else:
            disk_usage_by_files = round(100 * total / disk_size, 2)

        if size_array:
            mean_size = round(statistics.mean(size_array), 2)
            median_size = statistics.median(size_array)
        else:
            mean_size = None
            median_size = None

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'file_size_total': total,
                       'file_size_mean': mean_size,
                       'file_size_median': median_size,
                       'disk_usage_by_files': disk_usage_by_files
                       }
        return res
