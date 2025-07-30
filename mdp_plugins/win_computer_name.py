import os
import re

from Registry import Registry

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


# Note: This plugin might collect personal information
class WinComputerAndUserName(object):

    name = 'computer_and_user_names'
    description = 'Gets computer name and user names from the Windows registry'
    include_in_data_table = True


    @staticmethod
    def get_usernames_from_sam(files):
        temp_filename = 'export.bin'
        user_names = []

        for each_file in files:
            if re.search('Windows/System32/config/SAM$', each_file.full_path, re.IGNORECASE) is not None:

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                try:
                    users_key = reg.open(r"SAM\Domains\Account\Users\Names")
                    for user_key in users_key.subkeys():
                        user_names.append(user_key.name())
                    break
                except Registry.RegistryKeyNotFoundException:
                    print("Could not find Users Names key in SAM")

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        return user_names

    @staticmethod
    def get_computer_name(files):
        temp_filename = 'export.bin'
        computer_name = None
        for each_file in files:
            if re.search('Windows/System32/config/system$', each_file.full_path, re.IGNORECASE) is not None:

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                try:
                    key = reg.open("ControlSet001\\Control\\ComputerName\\ComputerName")
                    computer_name_val = key.value('ComputerName')
                    computer_name = computer_name_val.value()
                    break
                except Registry.RegistryKeyNotFoundException:
                    print('key not found')
                    computer_name = 'N/A'
                    break
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return computer_name

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        user_names = self.get_usernames_from_sam(files)
        computer_name = self.get_computer_name(files)


        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'computer_name': str(computer_name),
                        'user_names': ';'.join(user_names) if user_names else None} #TODO
        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinComputerAndUserName()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
