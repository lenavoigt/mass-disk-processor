import os
import re

from Registry import Registry

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class WinWifiCount(object):

    name = 'win_wifi_profiles'
    description = 'Checks Windows registry for number of wifi profiles. (Win Vista+)'
    include_in_data_table = True

    @staticmethod
    def get_wifi_profiles(files):
        # source: https://www.cybertriage.com/blog/how-to-find-evidence-of-network-windows-registry/
        #   HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Profiles

        wifi_profile_count = None

        temp_filename = 'export.bin'

        for each_file in files:
            
            if re.search('Windows/System32/config/SOFTWARE$', each_file.full_path, re.IGNORECASE) is not None:

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                key = r"Microsoft\Windows NT\CurrentVersion\NetworkList\Profiles"
                try:
                    reg_key = reg.open(key)
                    wifi_profile_count = 0
                    for profile in reg_key.subkeys():
                        profile_name = profile.name().lower()
                        print(f"\tFound wifi profile: {profile_name}")
                        wifi_profile_count += 1
                    print("in registry: NetworkList\Profiles")

                except Registry.RegistryKeyNotFoundException:
                    # print(f"Registry key not found: {key}")
                    continue

                os.remove(temp_filename)

        return wifi_profile_count

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files
        wifi_profile_count = self.get_wifi_profiles(files)

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'num_wifi_profiles': wifi_profile_count}

        return res

# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinWifiCount()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
