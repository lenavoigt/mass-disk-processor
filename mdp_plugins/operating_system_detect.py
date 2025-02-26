import re

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class EstimateOS(object):

    name = 'operating_system'
    description = 'Check for OS present'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files
        
        win_found = False
        lin_found = False
        mac_found = False

        # This is a very basic approach and a more advanced version of this could be written
        for each_file in files:
            if re.search('Windows/System32/config/software$', each_file.full_path, re.IGNORECASE) is not None:
                win_found = True
                # print('Windows found')

            if re.search('System/Library/CoreServices/SystemVersion.plist', each_file.full_path, re.IGNORECASE) is not None:
                mac_found = True
                # print('macOS found')

            if re.search('var/log/syslog', each_file.full_path, re.IGNORECASE) is not None:
                lin_found = True
                # print('Linux found')

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)

        res.results = {'windows_found': str(win_found), # multiple os can be reported if they are present
                       'linux_found': str(lin_found),
                       'mac_found': str(mac_found)
                       }

        return res



