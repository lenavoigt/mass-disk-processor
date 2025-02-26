import os.path
import re

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class WinNumberOfUserLNKFiles(object):

    name = 'win_no_user_lnk_files'
    description = 'Number of LNK files within the user folder (all users)'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        count = None
        total_recents = None
        max_recents = None
        total_starts = None
        max_starts = None
        windows_path_exists = False

        for each in files:
            if re.match(r'P_[0-9]+/Windows/', each.full_path, re.IGNORECASE):
                windows_path_exists = True
                break

        # Finds path for user folders or none if not present
        home_folder_base_path = None
        poss = ['Users', 'Documents and Settings', 'Dokumente und Einstellungen']
        for each_home_loc in poss:
            for each_file in files:
                if re.match(r'P_[0-9]+/{}/'.format(each_home_loc), each_file.full_path, re.IGNORECASE):
                    home_folder_base_path = each_home_loc

        # print('home loc = {}'.format(home_folder_base_path))


        if home_folder_base_path and windows_path_exists:
            count = 0

            for each in files:
                if re.match('P_[0-9]+/{}/.*\\.lnk$'.format(home_folder_base_path), each.full_path, re.IGNORECASE):
                    count += 1

            # Get list of user folders
            user_folders = []
            for each in files:
                res = re.match('P_[0-9]+/{}/([^/]*?)/'.format(home_folder_base_path), each.full_path, re.IGNORECASE)
                if res is not None:
                    if res.group(1) not in user_folders:
                        user_folders.append(res.group(1))

            # count link files per user
            recent_counts = {}
            for each_user in user_folders:
                if home_folder_base_path == 'Users':
                    recent_reg_ex = 'P_[0-9]+/.*{}/AppData/Roaming/Microsoft/Windows/Recent/.*\\.lnk$'.format(each_user)
                else:
                    recent_reg_ex = 'P_[0-9]+/.*{}/Recent/.*\\.lnk$'.format(each_user)
                recent_counts[each_user] = 0
                for each_file in files:
                    if re.match(recent_reg_ex, each_file.full_path, re.IGNORECASE):
                        recent_counts[each_user] += 1

            # count start menu link files per user
            start_menu_counts = {}
            for each_user in user_folders:
                if home_folder_base_path == 'Users':
                    recent_reg_ex = 'P_[0-9]+/.*{}/AppData/Roaming/Microsoft/Windows/Start Menu/.*\\.lnk$'.format(each_user)
                else:
                    recent_reg_ex = 'P_[0-9]+/.*{}/Start Menu/.*\\.lnk$'.format(each_user)
                start_menu_counts[each_user] = 0
                for each_file in files:
                    if re.match(recent_reg_ex, each_file.full_path, re.IGNORECASE):
                        start_menu_counts[each_user] += 1

            # work out max and totals for each...

            total_recents = 0
            for each in recent_counts:
                total_recents += recent_counts[each]

            max_recents = 0
            for each in recent_counts:
                if recent_counts[each] > max_recents:
                    max_recents = recent_counts[each]

            total_starts = 0
            for each in start_menu_counts:
                total_starts += start_menu_counts[each]

            max_starts = 0
            for each in start_menu_counts:
                if start_menu_counts[each] > max_starts:
                    max_starts = start_menu_counts[each]


        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'no_lnk_files_in_user_folders': count,
                       'no_recent_lnk_total': total_recents,
                       'no_recent_lnk_max': max_recents,
                       'no_start_menu_lnk_total': total_starts,
                       'no_start_menu_lnk_max': max_starts,

                       }
        return res

# just a way to test a plugin quickly
if __name__ == '__main__':
    a = WinNumberOfUserLNKFiles()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)

