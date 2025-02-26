import datetime
import os
import re
import struct

from Registry import Registry

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class WinOSLifespan(object):

    name = 'win_os_lifespan'
    description = 'Gets the installation date of Windows from Registry'
    include_in_data_table = True

    def get_win_install_date(self, files):
        temp_filename = 'export.bin'
        installdate = ''

        for each_file in files:
            if re.match(r'P_[0-9]+/Windows/System32/config/software$', each_file.full_path, re.IGNORECASE) is not None:
                # print('reg found')
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                # Have an exported file at this point so need to process as registry
                # TODO update Marple so that file export is not necessary
                # Can probably use f = io.BytesIO(b"some initial binary data: \x00\x01")

                reg = Registry.Registry(temp_filename)

                try:
                    key = reg.open("Microsoft\\Windows NT\\CurrentVersion")
                    install_date_val = key.value('InstallDate')
                    # print(install_date_val.value())
                    #
                    # for value in key.values():
                    #     print(value.name(), value.value())

                    installdate = datetime.datetime.utcfromtimestamp(install_date_val.value())
                    # print(installdate)
                    break

                except Registry.RegistryKeyNotFoundException:
                    # print('Windows CurrentVersion key not found')
                    installdate = None
                    break

        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return installdate


    def get_win_last_shutdown(self, files):
        temp_filename = 'export.bin'
        last_shutdown = ''

        for each_file in files:
            if re.search('P_[0-9]+/Windows/System32/config/system$', each_file.full_path, re.IGNORECASE) is not None:
                # print('reg found (system)')
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                # get CurrentControlSet...
                try:
                    current_control_set = reg.open("Select")
                    select__reg_val = current_control_set.value('Current')
                    select_val = select__reg_val.value()
                    # print('select val: {}'.format(select_val))
                except Registry.RegistryKeyNotFoundException:
                    # print('Windows CurrentControlSet Select key not found')
                    break

                system_win_key_path = "ControlSet00{}\\Control\\Windows".format(select_val)

                # Get Windows Control key...
                try:
                    system_win_key = reg.open(system_win_key_path)
                except Registry.RegistryKeyNotFoundException:
                    # print('Windows key {} not found'.format(system_win_key_path))
                    break

                # Get Shutdown value
                try:
                    shutdown_val_data = system_win_key.value('ShutdownTime')
                    # print(shutdown_val_data.value())
                    time_int = struct.unpack("<Q", shutdown_val_data.value())[0]
                    as_unix = (time_int - 116444736000000000) / 10000000
                    res = datetime.datetime.utcfromtimestamp(as_unix)

                    # for value in system_win_key.values():
                    #     print(value.name(), value.value())


                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

                    return res
                except Registry.RegistryValueNotFoundException:
                    # print('ShutdownTime value not found')
                    break

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        install_date = self.get_win_install_date(files)
        last_shutdown = self.get_win_last_shutdown(files)

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)

        res.results = {}
        if install_date is not None:
            res.results['windows_install_time'] = str(install_date)
        else:
            res.results['windows_install_time'] = ''

        if last_shutdown is not None:
            res.results['windows_last_shutdown_time'] = str(last_shutdown)
        else:
            res.results['windows_last_shutdown_time'] = ''


        res.results['windows_install_year_month'] = res.results['windows_install_time'][0:7]
        res.results['windows_last_shutdown_year_month'] = res.results['windows_last_shutdown_time'][0:7]
        res.results['windows_install_year'] = res.results['windows_install_time'][0:4]
        res.results['windows_last_shutdown_year'] = res.results['windows_last_shutdown_time'][0:4]

        if last_shutdown is not None and install_date is not None:
            diff_datetime = last_shutdown - install_date
            diff_in_secs = diff_datetime.days * 24 * 3600 + diff_datetime.seconds   #  might be able to replace with .total_seconds()
            # diff_str = str(diff_datetime)
            # print('diff: {} ({})'.format(diff_in_secs, diff_str))
        else:
            diff_datetime = ''
            diff_in_secs = ''

        res.results['win_os_lifetime'] = diff_in_secs
        res.results['win_os_lifetime_str'] = str(diff_datetime)

        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinOSLifespan()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
