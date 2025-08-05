import os
import re

from Registry import Registry

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class WinScreenResolution(MDPPlugin):
    name = 'win_screen_resolution'
    description = 'Gets information about (latest set) screen resolution from the Windows registry (Win 7+)'
    expected_results = ['screen_resolution_x', 'screen_resolution_y', 'screen_ratio', 'screen_pixels']

    def get_screen_resolution_x_y(self, files):

        temp_filename = 'export.bin'

        latest_change = 0
        latest_change_guid = 'unknown'
        screen_resolution_x = None
        screen_resolution_y = None

        for each_file in files:
            if re.search('Windows/System32/config/system$', each_file.full_path, re.IGNORECASE) is not None:
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                try:
                    key = reg.open("ControlSet001\\Control\\GraphicsDrivers\\Configuration")
                    guids = key.subkeys()

                    # print(guids)

                    # Find guid with the latest timestamp
                    for guid in guids:
                        for value in guid.values():
                            if value.name() == 'Timestamp':
                                if value.value() > latest_change:
                                    latest_change = value.value()
                                    latest_change_guid = guid.name()

                    # print(latest_change_guid)

                    # Select screen resolution from guid with latest timestamp
                    for guid in guids:
                        if guid.name() == latest_change_guid:
                            guid_subkeys = guid.subkeys()
                            for value in guid_subkeys[0].values():
                                if value.name() == 'PrimSurfSize.cx':
                                    screen_resolution_x = value.value()
                                if value.name() == 'PrimSurfSize.cy':
                                    screen_resolution_y = value.value()
                    break

                except Registry.RegistryKeyNotFoundException:
                    # print('key not found')
                    pass  # do nothing as filename might match non main registry then terminates without getting to the real one

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        return screen_resolution_x, screen_resolution_y

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        screen_resolution_x, screen_resolution_y = self.get_screen_resolution_x_y(files)

        result = self.create_result(target_disk_image)
        self.set_results(result, {
            'screen_resolution_x': screen_resolution_x,
            'screen_resolution_y': screen_resolution_y,
            'screen_ratio': screen_resolution_x / screen_resolution_y if screen_resolution_x and screen_resolution_y else None,
            'screen_pixels': screen_resolution_x * screen_resolution_y if screen_resolution_x and screen_resolution_y else None,
        })

        return result
