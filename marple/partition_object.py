import json

class PartitionItem(object):

    def __init__(self, start, end, partition_type, allocated=True):

        self.start_sector = start
        self.end_sector = end
        self.length = end-start+1
        self.type = partition_type
        self.allocated = allocated
        self.files = None

    def __str__(self):
        return "{}".format(json.dumps(self.to_dict()))

    def to_dict(self):
        res = {}
        res['start_sector'] = self.start_sector
        res['end_sector'] = self.end_sector
        res['length'] = self.length
        res['type'] = self.type
        res['allocated'] = self.allocated
        return res


    def __eq__(self, other):
        if self.start_sector != other.start_sector:
            return False
        if self.end_sector != other.end_sector:
            return False
        if self.length != other.length:
            return False
        if self.type != other.type:
            return False
        if self.allocated != other.allocated:
            return False

        return True
