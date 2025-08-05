import re

from mdp_lib.mdp_plugin import MDPPlugin
from mdp_lib.disk_image_info import TargetDiskImage

class WinNumberOfPrefetchFiles(MDPPlugin):

    name = 'win_no_prefetch_files'
    description = 'Number of prefetch files within the folder Windows/Prefetch'
    expected_results = ['no_prefetch_files']

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

        result = self.create_result(target_disk_image)
        self.set_results(result, {'no_prefetch_files': count})
        return result