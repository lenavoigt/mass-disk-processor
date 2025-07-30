import logging
import os
import re

from Registry import Registry

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class WinUSBCount(object):

    name = 'win_no_usbs'
    description = 'Scrapes Setupapi for attached USB mass storage devices, checks Windows registry for USB'
    include_in_data_table = True

    @staticmethod
    def get_setup_api_usb(files):
        temp_filename = 'export.bin'
        usb_count = None
        for each_file in files:
            if re.search(r'setupapi(\.dev)?\.log$', each_file.full_path, re.IGNORECASE) is not None:
                # print('reg found')
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                f = open(temp_filename, 'rb')
                usb_count = 0
                for each_line in f:
                    try:
                        # XP
                        if re.search(r'#I123.*?USBSTOR\\DISK&VEN_.*?"', each_line.decode('utf-8')) is not None:
                            usb_count += 1
                        # Windows Vista and newer
                        if re.search("Device Install \(Hardware initiated\) - USB\\\\VID_(.{4})&PID_(.{4})\\\\(.+)",
                                     each_line.decode('utf-8')) is not None:
                            usb_count += 1
                        elif re.search("Device Install \(Hardware initiated\) - SWD\\\\WPDBUSENUM\\\\_\?\?_USBSTOR#",
                                       each_line.decode('utf-8')) is not None:
                            usb_count += 1
                    except UnicodeDecodeError as e:
                        logging.error(e)

                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
        return usb_count

    @staticmethod
    def get_reg_usb(files):
        # source: https://www.magnetforensics.com/blog/artifact-profile-usb-devices/
        # Windows XP:
        #     HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\USB\
        #     HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\USBSTOR\
        # Windows 7+:
        #     HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows Portable Devices\Devices
        # Windows 8/8.1+:
        #     HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\DeviceClasses
        # Windows 10 and Windows 11:
        #     HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\usbccgp
        #     HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\usbhub
        # Additional:
        #     HKEY_LOCAL_MACHINE\SYSTEM\MountedDevices
        #     HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist.
        reg_usb_count = reg_usbstor_count = reg_portable_dev = reg_dev_classes = reg_usbccgp = reg_usbhub = reg_mounted_dev = reg_user_assist = None

        temp_filename = 'export.bin'

        for each_file in files:

            # Check for usb-related registry keys in software hive
            if re.search('Windows/System32/config/SOFTWARE$', each_file.full_path, re.IGNORECASE) is not None:

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                relevant_registry_keys = [r"Microsoft\Windows Portable Devices\Devices", r"Microsoft\Windows\CurrentVersion\Explorer\UserAssist"]


                for key in relevant_registry_keys:
                    try:
                        reg_key = reg.open(key)
                        value_count = 0
                        for dev in reg_key.subkeys():
                            dev_name = dev.name().lower()
                            print(f"\tFound dev: {dev_name}")
                            value_count += 1
                        if key == r"Microsoft\Windows Portable Devices\Devices":
                            reg_portable_dev = value_count
                            print("in registry: Windows Portable Devices")
                        elif key == r"Microsoft\Windows\CurrentVersion\Explorer\UserAssist":
                            reg_user_assist = value_count
                            print("in registry: UserAssist")

                    except Registry.RegistryKeyNotFoundException:
                        # print(f"Registry key not found: {key}")
                        continue

                os.remove(temp_filename)

            # Check for usb-related registry keys in system hive
            if re.search('Windows/System32/config/system$', each_file.full_path, re.IGNORECASE) is not None:

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                relevant_registry_keys = [r"ControlSet001\Enum\USB",
                                          r"ControlSet001\Enum\USBSTOR",
                                          r"ControlSet001\Control\DeviceClasses",
                                          r"ControlSet001\Services\usbccgp",
                                          r"ControlSet001\Services\usbhub",
                                          r"MountedDevices"]

                for key in relevant_registry_keys:
                    try:
                        reg_key = reg.open(key)
                        value_count = 0
                        for dev in reg_key.subkeys():
                            dev_name = dev.name().lower()
                            print(f"\tFound dev: {dev_name}")
                            value_count += 1
                        if key == r"ControlSet001\Enum\USB":
                            reg_usb_count = value_count
                            print("in registry: USB")
                        elif key == r"ControlSet001\Enum\USBSTOR":
                            reg_usbstor_count = value_count
                            print("in registry: USBSTOR")
                        elif key ==  r"ControlSet001\Control\DeviceClasses":
                            reg_dev_classes = value_count
                            print("in registry: DeviceClasses")
                        elif key == r"ControlSet001\Services\usbccgp":
                            reg_usbccgp = value_count
                            print("in registry: USBCCGP")
                        elif key == r"ControlSet001\Services\usbhub":
                            reg_usbhub = value_count
                            print("in registry: USBHUB")
                        elif key == r"MountedDevices":
                            reg_mounted_dev = value_count
                            print("in registry: MountedDevices")

                    except Registry.RegistryKeyNotFoundException:
                        # print(f"Registry key not found: {key}")
                        continue

                os.remove(temp_filename)

        return reg_usb_count, reg_usbstor_count, reg_portable_dev, reg_dev_classes, reg_usbccgp, reg_usbhub, reg_mounted_dev, reg_user_assist

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        setup_api_usb_count = self.get_setup_api_usb(files)

        reg_usb_count, reg_usbstor_count, reg_portable_dev, reg_dev_classes, reg_usbccgp, reg_usbhub, reg_mounted_dev, reg_user_assist = self.get_reg_usb(files)

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'num_usb_mass_storage_attached_setupapi': setup_api_usb_count,
                       'num_usb_reg_USB': reg_usb_count,
                       'num_usb_reg_USBSTOR': reg_usbstor_count,
                       'num_usb_reg_portable_dev': reg_portable_dev,
                       'num_usb_reg_dev_classes': reg_dev_classes,
                       'num_usb_reg_usbccgp': reg_usbccgp,
                       'num_usb_reg_usbhub': reg_usbhub,
                       'num_usb_reg_mounted_dev': reg_mounted_dev,
                       'num_usb_reg_user_assist': reg_user_assist
                       }

        return res

# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinUSBCount()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
