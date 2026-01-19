import os
import re

from Registry import Registry

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class WinVersion(MDPPlugin):
    name = 'win_version'
    description = 'Gets detail about Windows version from Registry'
    expected_results = ['win_build', 'win_build_inferred_os', 'win_registered_org_present',
                        'win_registered_owner_present', 'win_version_id', 'win_version_str']

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'

        win_build = None
        win_build_inferred_os = None
        win_registered_org_present = None
        win_registered_owner_present = None
        win_version_id = None
        win_version_str = None

        for each_file in files:
            if re.search('Windows/System32/config/software$', each_file.full_path, re.IGNORECASE) is not None:

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                try:
                    key = reg.open("Microsoft\\Windows NT\\CurrentVersion")
                except Registry.RegistryKeyNotFoundException:
                    # print('key not found')
                    break

                try:
                    version_val = key.value('ProductName')
                    win_version_str = version_val.value()
                except:
                    # print("reg value not found (ProductName)")
                    win_version_str = "unknown"

                try:
                    version_val = key.value('CurrentVersion')
                    win_version_id = version_val.value()
                except:
                    # print("reg value not found (CurrentVersion)")
                    win_version_id = "unknown"

                # try:
                #     version_val = key.value('ReleaseID')
                #     res.results['win_version_release'] = version_val.value()
                # except:
                #     print("reg value not found")
                #     res.results['win_version_release'] = "unknown"

                try:
                    version_val = key.value('CurrentBuild')  # > 22000 should indicate Win 11
                    win_build = version_val.value()
                    win_build_inferred_os = 'unknown'
                    is_server = "server" in win_version_str.lower()
                    try:
                        # https://en.wikipedia.org/wiki/List_of_Microsoft_Windows_versions
                        # https://www.gaijin.at/en/infos/windows-version-numbers
                        version_int = int(version_val.value())
                        if is_server and version_int == 26100:
                            win_build_inferred_os = 'Windows Server 2025'
                        elif is_server and version_int == 20348:
                            win_build_inferred_os = 'Windows Server 2022'
                        elif is_server and version_int == 17763:
                            win_build_inferred_os = 'Windows Server 2019'
                        elif is_server and version_int == 14393:
                            win_build_inferred_os = 'Windows Server 2016'
                        elif is_server and (version_int == 9200 or version_int == 9600):
                            win_build_inferred_os = 'Windows Server 2012'
                        elif is_server and version_int == 8400:
                            win_build_inferred_os = 'Windows Home Server 2011'
                        elif is_server and (version_int == 6001 or version_int == 6002 or version_int == 6003 or version_int == 7600 or version_int == 7601):
                            win_build_inferred_os = 'Windows Server 2008'
                        elif version_int >= 22000: # 22000 or 22621 or 22631 or 26100 or 26200
                            win_build_inferred_os = 'Windows 11'
                        elif version_int >= 10240:
                            win_build_inferred_os = 'Windows 10'
                        elif version_int == 9600:
                            win_build_inferred_os = 'Windows 8.1'
                        elif version_int == 9200:
                            win_build_inferred_os = 'Windows 8'
                        elif version_int == 7600 or version_int == 7601:
                            win_build_inferred_os = 'Windows 7'
                        elif version_int == 6000 or version_int == 6001 or version_int == 6002:
                            win_build_inferred_os = 'Windows Vista'
                        elif version_int == 2600 or version_int == 2700 or version_int == 2710 or version_int == 3790:
                            win_build_inferred_os = 'Windows XP'
                        elif version_int == 3000:
                            win_build_inferred_os = 'Windows ME'
                        elif version_int == 2195:
                            win_build_inferred_os = 'Windows 2000'
                        elif version_int == 1998 or version_int == 2222:
                            win_build_inferred_os = 'Windows 98'
                        elif version_int == 1057:
                            win_build_inferred_os = 'Windows NT 3.51'
                        elif version_int == 807:
                            win_build_inferred_os = 'Windows NT 3.5'
                    except ValueError:
                        if version_val.value() == '2222A':
                            win_build_inferred_os = 'Windows 98 SE'
                        elif version_val.value() == '1.511.1 () (Obsolete data - do not use)':
                            # CurrentBuild seems to have this value for XP
                            build_lab_val = key.value('BuildLab').value()
                            build_lab_str = build_lab_val.split('.')[0]
                            win_build = build_lab_str
                            build_number = int(build_lab_str)
                            if build_number == 2600 or build_number == 2700 or build_number == 2710 or build_number == 3790:
                                win_build_inferred_os = 'Windows XP'

                except:
                    # print("reg value not found")
                    win_build = "unknown"

                try:
                    version_val = key.value('RegisteredOwner')
                    if version_val.value() != "":
                        win_registered_owner_present = True
                    else:
                        win_registered_owner_present = True
                except:
                    # print("reg value not found (RegisteredOwner)")
                    break

                try:
                    version_val = key.value('RegisteredOrganization')
                    # print("'{}'".format(version_val.value()))
                    if version_val.value() != "":
                        win_registered_org_present = True
                    else:
                        win_registered_org_present = False
                except:
                    # print("reg value not found (RegisteredOrganization)")
                    break

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        result = self.create_result(target_disk_image)
        self.set_results(result, {'win_build': win_build,
                                  'win_build_inferred_os': win_build_inferred_os,
                                  'win_registered_org_present': win_registered_org_present,
                                  'win_registered_owner_present': win_registered_owner_present,
                                  'win_version_id': win_version_id,
                                  'win_version_str': win_version_str
                                  })

        return result
