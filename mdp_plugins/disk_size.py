from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class DiskSize(MDPPlugin):
    name = 'disk_size'
    description = 'Collects basic disk size information'
    expected_results = ["disk_size", "total_sectors"]

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

        res = self.create_result(target_disk_image)
        self.set_results(res, {
            "disk_size": self.get_disk_size(disk_image),
            "total_sectors": self.get_total_sectors(disk_image)
        })

        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = DiskSize()

    test_image_path = 'path to disk image'
    disk_image_object = TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
