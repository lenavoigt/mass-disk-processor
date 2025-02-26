import os
import re

import Evtx.Evtx as evtx
import xmltodict

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class EVTXLogs(object):

    name = 'win_evt_logs'
    description = 'Gets information from EVT logs'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'

        succ_login = None
        failed_login = None
        unlocks = None
        clock_change = None

        for each_file in files:
            if re.match('.*/winevt/Logs/Security.evtx$', each_file.full_path, re.IGNORECASE):
                # print(each_file.full_path)

                succ_login = 0
                failed_login = 0
                unlocks = 0
                clock_change = 0


                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                with evtx.Evtx(temp_filename) as log:
                    for record in log.records():
                        data_dict = xmltodict.parse(record.xml())
                        event_id = int(data_dict['Event']['System']['EventID']['#text'])
                        if event_id == 4624:    # successful login
                            for each in data_dict['Event']['EventData']['Data']:  # for this one we need to loop through to find the LogonType (2 is interactive logon)
                                if each.get('@Name') == 'LogonType':
                                    if each.get('#text') == '2':  # this is interactive logon
                                        succ_login += 1
                                    if each.get('#text') == '7':  # this is workstation unlock
                                        unlocks += 1
                        elif event_id == 4625:     # failed login (this one is more straight forward)
                            failed_login += 1
                        elif event_id == 4616:     # clock change (vista onwards https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4616)
                            clock_change += 1
                break  # stop if Security evtx is processed

        # some event log info :
        #    https://www.alteredsecurity.com/post/fantastic-windows-logon-types-and-where-to-find-credentials-in-them#viewer-5movr
        #    https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4624

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'evtx_success_logins_4624_2': succ_login,
                       'evtx_failed_logins_4625': failed_login,
                       'evtx_unlocks_4624_7': unlocks,
                       'evtx_clock_change_4616': clock_change
                       }
        return res

# just a way to test a plugin quickly
if __name__ == '__main__':
    a = EVTXLogs()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
