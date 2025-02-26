import os
import re

import Evtx.Evtx as evtx
import xmltodict

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class EVTXLoginsDetail(object):

    name = 'EVT logins details'
    description = 'Retrieves full list of login details from Security.evtx'
    include_in_data_table = False

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'

        # succ_login = 0
        login_list = []

        for each_file in files:
            if re.match('.*/winevt/Logs/Security.evtx$', each_file.full_path, re.IGNORECASE):
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                with evtx.Evtx(temp_filename) as log:
                    for record in log.records():
                        data_dict = xmltodict.parse(record.xml())
                        event_id = int(data_dict['Event']['System']['EventID']['#text'])
                        if event_id == 4624:    # successful login
                            username = 'unknown'
                            usersid = 'unknown'
                            login_type = 'unknown'
                            process_name = 'unknown '

                            timestamp = data_dict['Event']['System']['TimeCreated']['@SystemTime']

                            for each in data_dict['Event']['EventData']['Data']:  # for this one we need to loop through to collect details
                                if each.get('@Name') == 'LogonType':
                                    login_type = each.get('#text')
                                if each.get('@Name') == 'TargetUserName':
                                    username = each.get('#text')
                                if each.get('@Name') == 'TargetUserSid':
                                    usersid = each.get('#text')
                                if each.get('@Name') == 'ProcessName':
                                    process_name = each.get('#text')


                            if login_type == '2':
                                login_list.append({ 'event_id': event_id,
                                    'logintype': login_type,
                                    'timestamp': timestamp,
                                    'processname': process_name,
                                    'username': username,
                                    'usersid': usersid})

                break  # stop if Security evtx is processed

        # some event log info :
        #    https://www.alteredsecurity.com/post/fantastic-windows-logon-types-and-where-to-find-credentials-in-them#viewer-5movr
        #    https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4624

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = { 'logins': login_list}
        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = EVTXLoginsDetail()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)
