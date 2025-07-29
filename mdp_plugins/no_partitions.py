import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class NumberOfPartitions(object):

    name = 'no_partitions'
    description = 'Number of partitions'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        try:
            partitions = disk_image.partitions
            no_partitions = len(partitions)
        except Exception as e:
            print(e)
            no_partitions = None
        # print('no_partitions: {}'.format(no_partitions))

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'no_partitions': no_partitions}
        return res

