import re

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class NumberOfUserFiles(object):

    name = 'no_user_files'
    description = 'Number of files within the user folder (all users)'
    include_in_data_table = True

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

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'no_files_in_users_folder': count}
        return res

# just a way to test a plugin quickly
if __name__ == '__main__':
    a = NumberOfUserFiles()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
