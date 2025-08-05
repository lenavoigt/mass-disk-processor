import re
import struct

from Registry import Registry

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class UserInfo(MDPPlugin):
    name = 'win_user_info'
    description = 'Gets information about Windows users'
    expected_results = ['win_max_login_count', 'win_total_login_count', 'win_no_users']

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'
        login_count = None
        login_total = None
        no_users = None

        for each_file in files:
            if re.search('Windows/System32/config/SAM$', each_file.full_path, re.IGNORECASE) is not None:
                # print('reg found (SAM)')
                # print(each_file.full_path)

                f = open(temp_filename, 'wb')
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                users_range = ['000003E8', '000003E9', '000003EA', '000003EB', '000003EC',
                               '000003ED', '000003EF']

                range_of_login_counts = []
                for each_user in users_range:
                    key_path = "SAM\\Domains\\Account\\Users\\{}".format(each_user)
                    try:
                        key = reg.open(key_path)
                    except Registry.RegistryKeyNotFoundException:
                        # print('User key {} not found'.format(key_path))
                        continue  # don't do the rest of this loop iteration

                    try:
                        # TODO: there is a invalid login count too that could be extracted + last login time? + last pw change?
                        data = key.value('F').value()
                        login_count_data = data[66:68]
                        this_login_count = struct.unpack("<H", login_count_data)[0]
                        range_of_login_counts.append(this_login_count)
                    except Registry.RegistryKeyNotFoundException:
                        # print('user key data not found')
                        continue

                if not range_of_login_counts:
                    login_count = None
                    login_total = None
                    no_users = None
                else:
                    login_count = max(range_of_login_counts)
                    login_total = sum(range_of_login_counts)
                    no_users = len(range_of_login_counts)

        result = self.create_result(target_disk_image)
        self.set_results(result, {'win_max_login_count': login_count, 'win_total_login_count': login_total,
                                  'win_no_users': no_users})

        return result
