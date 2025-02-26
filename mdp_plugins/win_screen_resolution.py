# from distutils.command.install import value

import os
import re

from Registry import Registry

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class WinScreenResolution(object):

    name = 'win_screen_resolution'
    description = 'Gets information about screen resolution from the Windows registry'
    # TODO: add support for other windows versions
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

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

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        # res.results['screen_resolution_guid'] = latest_change_guid
        res.results['screen_resolution_x'] = screen_resolution_x
        res.results['screen_resolution_y'] = screen_resolution_y
        if screen_resolution_x is not None and screen_resolution_y is not None:
            res.results['screen_ratio'] = screen_resolution_x / screen_resolution_y
            res.results['screen_pixels'] = screen_resolution_x * screen_resolution_y
        else:
            res.results['screen_ratio'] = None
            res.results['screen_pixels'] = None

        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinScreenResolution()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
