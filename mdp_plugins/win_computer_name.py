import os
import re

from Registry import Registry

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


# Note: This plugin was only created to test registry access, probably not too interesting
class WinComputerName(object):

    name = 'Computer Name'
    description = 'Gets computer name from the Windows registry'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'
        computername = None

        for each_file in files:
            if re.search('Windows/System32/config/system$', each_file.full_path, re.IGNORECASE) is not None:
                # print('reg found')
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                try:
                    key = reg.open("ControlSet001\\Control\\ComputerName\\ComputerName")
                    computername_val = key.value('ComputerName')
                    computername = computername_val.value()
                    break

                    # for value in key.values():
                    #     print(value.name(), value.value())
                except Registry.RegistryKeyNotFoundException:
                    print('key not found')
                    computername = 'N/A'
                    break

        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'computer_name': str(computername)}
        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinComputerName()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
