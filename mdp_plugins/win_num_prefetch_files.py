import re

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class WinNumberOfPrefetchFiles(object):

    name = 'win_no_prefetch_files'
    description = 'Number of prefetch files within the folder Windows/Prefetch'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        count = None
        prefetch_path_exists = False

        for each in files:
            if re.match(r'P_[0-9]+/Windows/Prefetch/', each.full_path, re.IGNORECASE):
                prefetch_path_exists = True
                break

        if prefetch_path_exists:
            count = 0
            for each in files:
                if re.match('P_[0-9]+/Windows/Prefetch/.*\\.pf$', each.full_path, re.IGNORECASE):
                    count += 1

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'no_prefetch_files': count}
        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinNumberOfPrefetchFiles()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
