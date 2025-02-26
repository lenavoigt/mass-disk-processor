import os
import re

from Registry import Registry

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class WinApps(object):
    name = 'win_apps'
    description = 'Gets information about the installed apps.'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'

        uninstall_registry = None
        app_path_registry = None

        for each_file in files:

            # Check for installed apps in registry
            if re.search('Windows/System32/config/SOFTWARE$', each_file.full_path, re.IGNORECASE) is not None:
                # print('reg found (SOFTWARE)')
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                relevant_registry_keys = ["Microsoft\\Windows\\CurrentVersion\\Uninstall",
                                          "Microsoft\\Windows\\CurrentVersion\\App Paths"]

                for key in relevant_registry_keys:
                    try:
                        reg_key = reg.open(key)
                        # print(f"Opened registry key: {key}")
                        app_count = 0
                        for application in reg_key.subkeys():
                            # application_name = application.name().lower()
                            # print(f"Found application: {application_name}")
                            app_count += 1
                        if "Uninstall" in key:
                            uninstall_registry = app_count
                        elif "Paths" in key:
                            app_path_registry = app_count

                    except Registry.RegistryKeyNotFoundException:
                        # print(f"Registry key not found: {key}")
                        break

                os.remove(temp_filename)

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)

        res.results = {'win_app_count_uninstall_registry': uninstall_registry,
                       'win_app_count_app_path_registry': app_path_registry,
                       }
        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinApps()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
