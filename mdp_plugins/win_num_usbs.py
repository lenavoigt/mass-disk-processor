import logging
import os
import re

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class USBCountWinSetupApi(object):

    name = 'win_no_usbs'
    description = 'Scrapes Setupapi for attached USB mass storage devices'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'
        usb_count = None
        for each_file in files:
            if re.search('setupapi.dev.log$', each_file.full_path, re.IGNORECASE) is not None:
                # print('reg found')
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                f = open(temp_filename, 'rb')
                usb_count = 0
                for each_line in f:
                    try:
                        if re.search("Device Install \(Hardware initiated\) - USB\\\\VID_(.{4})&PID_(.{4})\\\\(.+)", each_line.decode('utf-8')) is not None:
                            usb_count +=1
                        elif re.search("Device Install \(Hardware initiated\) - SWD\\\\WPDBUSENUM\\\\_\?\?_USBSTOR#", each_line.decode('utf-8')) is not None:
                            usb_count +=1
                    except UnicodeDecodeError as e:
                        logging.error(e)

                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'num_usb_mass_storage_attached_setupapi': usb_count}

        return res

# just a way to test a plugin quickly
if __name__ == '__main__':
    a = USBCountWinSetupApi()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
