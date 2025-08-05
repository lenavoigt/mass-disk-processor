import datetime
import os
import re
import struct

from Registry import Registry

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class WinOSLifespan(MDPPlugin):
    name = 'win_os_lifespan'
    description = 'Gets the installation date of Windows from Registry'
    expected_results = [
        'windows_install_time',
        'windows_last_shutdown_time',
        'windows_install_year_month',
        'windows_last_shutdown_year_month',
        'windows_install_year',
        'windows_last_shutdown_year',
        'win_os_lifetime',
        'win_os_lifetime_str'
    ]

    def get_win_install_date(self, files):
        temp_filename = 'export.bin'
        installdate = None

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
                    break

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        return installdate

    def get_win_last_shutdown(self, files):
        temp_filename = 'export.bin'
        last_shutdown = None

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
                    last_shutdown = datetime.datetime.utcfromtimestamp(as_unix)

                    # for value in system_win_key.values():
                    #     print(value.name(), value.value())

                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

                    return last_shutdown
                except Registry.RegistryValueNotFoundException:
                    # print('ShutdownTime value not found')
                    break

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        return last_shutdown

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        install_date = self.get_win_install_date(files)
        last_shutdown = self.get_win_last_shutdown(files)

        install_str = str(install_date) if install_date else None
        shutdown_str = str(last_shutdown) if last_shutdown else None

        result_values = {
            'windows_install_time': install_str,
            'windows_last_shutdown_time': shutdown_str,
            'windows_install_year_month': install_str[:7] if install_str else None,
            'windows_last_shutdown_year_month': shutdown_str[:7] if shutdown_str else None,
            'windows_install_year': install_str[:4] if install_str else None,
            'windows_last_shutdown_year': shutdown_str[:4] if shutdown_str else None
        }

        if install_date and last_shutdown:
            diff_datetime = last_shutdown - install_date
            result_values[
                'win_os_lifetime'] = diff_datetime.days * 24 * 3600 + diff_datetime.seconds  # might be able to replace with .total_seconds()
            result_values['win_os_lifetime_str'] = str(diff_datetime)
        else:
            result_values['win_os_lifetime'] = None
            result_values['win_os_lifetime_str'] = None

        result = self.create_result(target_disk_image)
        self.set_results(result, result_values)

        return result
