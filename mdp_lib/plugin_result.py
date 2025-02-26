import pprint
import datetime

class MDPResult(object):

    def __init__(self, source_file, plugin, desc):
        self.source_file = source_file
        self.plugin = plugin
        self.desc = desc
        self.results = {}
        self.include_in_data_table = False
        self.time_created = str(datetime.datetime.now())

    def __str__(self):
        output = {'results': self.results,
                  'source_file': self.source_file,
                  'plugin': self.plugin,
                  'description': self.desc,
                  'time_created': self.time_created}

        return "{}".format(pprint.pformat(output))
