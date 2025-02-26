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
        for each in files:
            size_array.append(each.file_size)
            total += each.file_size

        try:
            ds = mdp_plugins.disk_size.DiskSize()
            disk_size = ds.get_disk_size(disk_image)
        except Exception as e:
            print(e)
            disk_size = None

        if disk_size is None:
            disk_usage = None
        else:
            disk_usage = round(100 * total / disk_size, 2)

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'file_size_total': total,
                       'file_size_mean': round(statistics.mean(size_array),2),
                       'file_size_median': statistics.median(size_array),
                       'disk_usage_percent': disk_usage,
                       }
        return res
