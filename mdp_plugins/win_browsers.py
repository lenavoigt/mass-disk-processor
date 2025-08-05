import os
import re

from Registry import Registry

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class WinBrowsers(MDPPlugin):
    name = 'win_browsers'
    description = 'Gets information about the installed browsers and default browsers (currently only supports Edge, Chrome, Firefox).'
    expected_results = ['chrome_default', 'chrome_present', 'edge_default', 'edge_present', 'firefox_default',
                        'firefox_present']

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'
        edge_present = False
        edge_default = False
        chrome_present = False
        chrome_default = False
        firefox_present = False
        firefox_default = False
        registry_present = False

        for each_file in files:

            # Check for installed browsers in registry
            if re.search('Windows/System32/config/SOFTWARE$', each_file.full_path, re.IGNORECASE) is not None:
                # print('reg found (SOFTWARE)')
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                # TODO: check filesize is > 0
                try:
                    reg = Registry.Registry(temp_filename)
                except Exception:  # TODO: work out what the correct exception to handle is!
                    print('error opening registry file: {} ({} bytes)'.format(each_file.full_path, each_file.file_size))
                    break

                relevant_registry_keys = ["Microsoft\\Windows\\CurrentVersion\\Uninstall",
                                          "Microsoft\\Windows\\CurrentVersion\\App Paths"]

                for key in relevant_registry_keys:
                    try:
                        reg_key = reg.open(key)
                        # print(f"Opened registry key: {key}")
                        registry_present = True

                        for application in reg_key.subkeys():
                            application_name = application.name().lower()
                            # print(f"Found application: {application_name}")

                            if "msedge" in application_name or "iexplore" in application_name:
                                edge_present = True
                                # print('Edge detected!')
                            elif "chrome" in application_name:
                                chrome_present = True
                                # print('Chrome detected!')
                            elif "firefox" in application_name or "mozilla" in application_name:
                                firefox_present = True
                                # print('Firefox detected!')
                            # else:
                            #     print("Unknown browser detected")
                    except Registry.RegistryKeyNotFoundException:
                        # print(f"Registry key not found: {key}")
                        break

                os.remove(temp_filename)

            # Check for default browsers in registry
            if re.search('NTUSER.DAT$', each_file.full_path, re.IGNORECASE) is not None:
                # print('reg found (ntuser.dat)')
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                # TODO: check filesize is > 0
                try:
                    reg = Registry.Registry(temp_filename)
                except Exception:  # TODO: work out what the correct exception to handle is!
                    print('error opening registry file: {} ({} bytes)'.format(each_file.full_path, each_file.file_size))
                    break

                # NOTE: Currently only going with one registry key
                relevant_registry_keys = [
                    "Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\https\\UserChoice",
                    # "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.html\\UserChoice",
                    # "Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" # for Windows XP
                    ]

                for key in relevant_registry_keys:
                    try:
                        reg_key = reg.open(key)
                        # print(f"Opened registry key: {key}")
                        registry_present = True
                        if "Internet Settings" in key:
                            browser_value = reg_key.value("User Agent").value().lower()
                        else:
                            browser_value = reg_key.value("ProgId").value().lower()

                        if "firefox" in browser_value or "mozilla" in browser_value:
                            # print("Default browser is Firefox")
                            firefox_default = True
                        elif "chrome" in browser_value:
                            # print("Default browser is Chrome")
                            chrome_default = True
                        elif "msedge" in browser_value or "iexplore" in browser_value:
                            # print("Default browser is Edge or Internet Explorer")
                            edge_default = True
                        # else:
                            # print("Unknown browser detected")
                    except Registry.RegistryKeyNotFoundException:
                        # print(f"Registry key not found: {key}")
                        # break
                        pass

                os.remove(temp_filename)

        if not registry_present:
            edge_present = None
            edge_default = None
            chrome_present = None
            chrome_default = None
            firefox_present = None
            firefox_default = None

        result = self.create_result(target_disk_image)
        self.set_results(result, {'edge_present': edge_present,
                                  'chrome_present': chrome_present,
                                  'firefox_present': firefox_present,
                                  'edge_default': edge_default,
                                  'chrome_default': chrome_default,
                                  'firefox_default': firefox_default
                                  })
        return result
