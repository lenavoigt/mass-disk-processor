from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class NumberOfPartitions(MDPPlugin):

    name = 'no_partitions'
    description = 'Number of partitions'
    expected_results = ['no_partitions']

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        try:
            partitions = disk_image.partitions
            no_partitions = len(partitions)
        except Exception as e:
            print(e)
            no_partitions = None
        # print('no_partitions: {}'.format(no_partitions))

        result = self.create_result(target_disk_image)
        self.set_result(result, 'no_partitions', no_partitions)
        return result
