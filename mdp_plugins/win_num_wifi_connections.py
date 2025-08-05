import os
import re

from Registry import Registry

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class WinWifiCount(MDPPlugin):
    name = 'win_wifi_profiles'
    description = 'Checks Windows registry for number of wifi profiles. (Win Vista+)'
    expected_results = ['num_wifi_profiles']

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
                        # print(f"\tFound wifi profile: {profile_name}")
                        wifi_profile_count += 1
                    # print("in registry: NetworkList\Profiles")

                except Registry.RegistryKeyNotFoundException:
                    # print(f"Registry key not found: {key}")
                    continue

                os.remove(temp_filename)

        return wifi_profile_count

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files
        wifi_profile_count = self.get_wifi_profiles(files)

        result = self.create_result(target_disk_image)
        self.set_results(result, {'num_wifi_profiles': wifi_profile_count})

        return result
