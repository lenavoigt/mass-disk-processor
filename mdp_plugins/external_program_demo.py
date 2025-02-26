import subprocess

import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class ExternalProgramDemo(object):

    name = 'external_demo'
    description = 'Demo plugin to show how to call external programs'
    include_in_data_table = False

    def process_disk(self, target_disk_image: TargetDiskImage):

        proc_result = subprocess.run(['stat', target_disk_image.image_path], stdout=subprocess.PIPE)
        output = proc_result.stdout.decode('utf-8')

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'output': output}

        return res
