import datetime

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class FSLifespan(MDPPlugin):
    name = 'fs_lifespan'
    description = 'Difference between earliest and latest file creation time'
    expected_results = [
        'lifespan_fs_cr',
        'lifespan_fs_cr_str',
        'earliest_fs_cr',
        'latest_fs_cr'
    ]

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

        diff = latest - earliest  # in seconds
        diff_datetime = datetime.datetime.fromtimestamp(latest) - datetime.datetime.fromtimestamp(earliest)
        diff_str = str(diff_datetime)
        # print('diff: {} ({})'.format(diff, diff_str))

        result = self.create_result(target_disk_image)
        self.set_results(result, {
            'lifespan_fs_cr': diff,
            'lifespan_fs_cr_str': diff_str,
            'earliest_fs_cr': earliest_str,
            'latest_fs_cr': latest_str
        })

        return result
