# from distutils.command.install import value

import os
import re

from Registry import Registry

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class WinVersion(object):

    name = 'win_version'
    description = 'Gets detail about Windows version from Registry'
    include_in_data_table = True

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
                    version_val = key.value('CurrentBuild')   # > 22000 should indicate Win 11
                    win_build = version_val.value()
                    win_build_inferred_os = 'unknown'
                    try:
                        # https://en.wikipedia.org/wiki/List_of_Microsoft_Windows_versions
                        version_int = int(version_val.value())
                        if version_int >= 22000:
                            win_build_inferred_os = 'Windows 11'
                        elif version_int >= 10240:
                            win_build_inferred_os = 'Windows 10'
                        elif version_int == 9600:
                            win_build_inferred_os = 'Windows 8.1'
                        elif version_int == 9200:
                            win_build_inferred_os = 'Windows 8'
                        elif version_int == 7600 or version_int == 7601:
                            win_build_inferred_os = 'Windows 7'
                        elif version_int == 6002:
                            win_build_inferred_os = 'Windows Vista'
                        elif version_int == 2600 or version_int == 2700 or version_int == 2710 or version_int == 3790:
                            win_build_inferred_os = 'Windows XP'
                        elif version_int == 3000:
                            win_build_inferred_os = 'Windows ME'
                        elif version_int == 2195:
                            win_build_inferred_os = 'Windows 2000'
                        elif version_int == 1998:
                            win_build_inferred_os = 'Windows 2000'
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
                    #print("reg value not found (RegisteredOrganization)")
                    break

        if os.path.exists(temp_filename):
            os.remove(temp_filename)


        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)

        res.results = {'win_build': win_build,
                       'win_build_inferred_os': win_build_inferred_os,
                       'win_registered_org_present': win_registered_org_present,
                       'win_registered_owner_present': win_registered_owner_present,
                       'win_version_id': win_version_id,
                       'win_version_str': win_version_str
                       }

        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinVersion()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
