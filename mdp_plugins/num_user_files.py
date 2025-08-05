import re

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class NumberOfUserFiles(MDPPlugin):

    name = 'no_user_files'
    description = 'Number of files within the user folder (all users)'
    expected_results = ['no_files_in_users_folder']

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        count = None
        user_path_exists = False

        for each in files:
            if (re.match(r'P_[0-9]+/Users/', each.full_path, re.IGNORECASE)
                    or re.match('P_[0-9]+/Documents and Settings/', each.full_path, re.IGNORECASE)
                    or re.match('P_[0-9]+/Dokumente und Einstellungen/', each.full_path, re.IGNORECASE)
                    or re.match('P_[0-9]+/home/', each.full_path)):
                user_path_exists = True
                break

        if user_path_exists:
            count = 0
            for each in files:
                if (re.match('P_[0-9]+/Users/.*', each.full_path)
                        or re.match('P_[0-9]+/Documents and Settings/.*', each.full_path)
                        or re.match('P_[0-9]+/Dokumente und Einstellungen/.*', each.full_path) # Is there a more elegant way to do this?
                        or re.match('P_[0-9]+/home/.*', each.full_path)):
                    count += 1

        result = self.create_result(target_disk_image)
        self.set_result(result, 'no_files_in_users_folder', count)
        return result
