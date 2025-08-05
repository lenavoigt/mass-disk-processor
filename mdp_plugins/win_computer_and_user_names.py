# import os
# import re
#
# from Registry import Registry

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin
from utils.windows_registry_utils import get_registry_value, get_current_control_set_number, list_registry_subkey_names


# Note: This plugin might collect personal information
class WinComputerAndUserName(MDPPlugin):
    name = 'computer_and_user_names'
    description = 'Gets computer name and user names from the Windows registry'
    expected_results = ['computer_name', 'user_names']

    # @staticmethod
    # def get_usernames_from_sam(files):
    #     temp_filename = 'export.bin'
    #     user_names = []
    #
    #     for each_file in files:
    #         if re.search('Windows/System32/config/SAM$', each_file.full_path, re.IGNORECASE) is not None:
    #
    #             f = open(temp_filename, 'wb')
    #             f.write(each_file.read())
    #             f.close()
    #
    #             reg = Registry.Registry(temp_filename)
    #
    #             try:
    #                 users_key = reg.open(r"SAM\Domains\Account\Users\Names")
    #                 for user_key in users_key.subkeys():
    #                     user_names.append(user_key.name())
    #                 break
    #             except Registry.RegistryKeyNotFoundException:
    #                 # print("Could not find Users Names key in SAM")
    #                 continue
    #
    #     if os.path.exists(temp_filename):
    #         os.remove(temp_filename)
    #
    #     return user_names

    # @staticmethod
    # def get_computer_name(files):
    #     temp_filename = 'export.bin'
    #     computer_name = None
    #     for each_file in files:
    #         if re.search('Windows/System32/config/system$', each_file.full_path, re.IGNORECASE) is not None:
    #
    #             f = open(temp_filename, 'wb')
    #             f.write(each_file.read())
    #             f.close()
    #
    #             reg = Registry.Registry(temp_filename)
    #
    #             try:
    #                 key = reg.open("ControlSet001\\Control\\ComputerName\\ComputerName")
    #                 computer_name_val = key.value('ComputerName')
    #                 computer_name = computer_name_val.value()
    #                 break
    #             except Registry.RegistryKeyNotFoundException:
    #                 # print('key not found')
    #                 computer_name = 'N/A'
    #                 break
    #     if os.path.exists(temp_filename):
    #         os.remove(temp_filename)
    #     return computer_name

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        # user_names = self.get_usernames_from_sam(files)
        # computer_name = self.get_computer_name(files)
        user_names = list_registry_subkey_names(files, "SAM", "SAM\\Domains\\Account\\Users\\Names")

        computer_name = None
        ccs = get_current_control_set_number(files)
        if ccs is not None:
            key_path = f"ControlSet00{ccs}\\Control\\ComputerName\\ComputerName"
            computer_name = get_registry_value(files, "SYSTEM", key_path, "ComputerName")

        result = self.create_result(target_disk_image)
        self.set_results(result, {'computer_name': computer_name,
                                  'user_names': ';'.join(user_names) if user_names else None})
        return result
