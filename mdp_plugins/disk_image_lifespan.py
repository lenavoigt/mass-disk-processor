import datetime

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class Lifespan(object):

    name = 'disk_lifespan'
    description = 'Difference between earliest and latest file creation time'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files

        sorted_list = sorted(files, key=lambda d: d.timestamps['cr_time'])

        earliest = sorted_list[0].timestamps['cr_time']
        earliest_str = datetime.datetime.fromtimestamp(earliest).isoformat()
        # print('earliest: {} ({}) {}'.format(sorted_list[0].full_path, earliest, earliest_str))
        latest = sorted_list[-1].timestamps['cr_time']
        latest_str = datetime.datetime.fromtimestamp(latest).isoformat()
        # print('latest: {} ({}) {}'.format(sorted_list[-1].full_path, latest, latest_str))

        diff = latest - earliest # in seconds
        diff_dateime = datetime.datetime.fromtimestamp(latest) - datetime.datetime.fromtimestamp(earliest)
        diff_str = str(diff_dateime)
        # print('diff: {} ({})'.format(diff, diff_str))

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'lifespan_fs_cr': diff,
                       'lifespan_fs_cr_str': diff_str,
                       'earliest_fs_cr': earliest_str,
                       'latest_fs_cr': latest_str}
        return res