import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class DiskSize(object):

    name = 'disk_size'
    description = 'Gets total size of the disk image (as raw)'
    include_in_data_table = True

    @staticmethod
    def get_disk_size(disk_image):
        disk_size = disk_image.get_media_size()

        return disk_size

    @staticmethod
    def get_total_sectors(disk_image):
        # This is derived from tsk partition information at the moment
        try:
            parts = disk_image._get_partitions()
            if not parts:
                return None
        except Exception as e:
            print(e)
            return None
        max_sector = max((part.start + part.len for part in parts), default=None)
        return max_sector


    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'disk_size': self.get_disk_size(disk_image),
                       'total_sectors': self.get_total_sectors(disk_image)}
        return res



# just a way to test a plugin quickly
if __name__ == '__main__':
    a = DiskSize()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
