import subprocess

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class ExternalProgramDemo(MDPPlugin):
    name = 'external_demo'
    description = 'Demo plugin to show how to call external programs'
    expected_results = ['output']
    include_in_data_table = False

    def process_disk(self, target_disk_image: TargetDiskImage):
        proc_result = subprocess.run(['stat', target_disk_image.image_path], stdout=subprocess.PIPE)
        output = proc_result.stdout.decode('utf-8')

        res = self.create_result(target_disk_image)
        self.set_results(res, {
            'output': output
        })

        return res
