import time
import hashlib

class FileItem(object):

    def __init__(self, full_path, inode, file_size, partition_sector):
        self.id = None
        self.path_to_disk_image = None
        self.partition_sector = partition_sector
        self.full_path = full_path
        self.meta_path = None
        self.evidence_name = None
        self.file_size = file_size
        self.timestamps = {}
        self.start_block = None
        self.blocks = []
        self.inode = inode
        self.sha1 = None
        self.signature: bytes|None = None

        self.__bytes_read = 0  # keeps track of sequential file reads

    def __str__(self):
        return "{}, {}".format(self.inode, self.full_path)

    def __eq__(self, other):
        if self.full_path != other.full_path:
            return False
        if self.inode != other.inode:
            return False
        return True

    def to_dict(self):
        a = {}
        a['id'] = self.id
        a['full_path'] = self.full_path
        a['meta_path'] = self.meta_path
        a['evidence_name'] = self.evidence_name
        a['inode'] = self.inode
        a['file_size'] = self.file_size
        a['partition_sector'] = self.partition_sector
        a['sha1'] = self.sha1
        #a['signature'] = self.to_hex(self.signature)
        if self.signature is not None:
            a['signature'] = self.signature.hex()
        else:
            a['signature'] = None
        a['timestamps'] = self.timestamps
        return a

    def to_hex(self, data):
        out_str = ""
        for each_byte in data:
            out_str += "{:02x}".format(each_byte)
        return out_str

    def populate_signature_field(self, signature_size=8, fs_handle=None):
        self.signature = self.read(signature_size,fs_handle)


    # default size limit for calculating a hash is 100MB
    def populate_hash_and_signature_field(self, signature_size=8,hash_size_limit=100000000, fs_handle=None):
        self.populate_signature_field(signature_size=signature_size,fs_handle=fs_handle)
        if self.file_size <= hash_size_limit:
            # print(f'Hashing file of size {self.file_size} at {time.time()}')
            sha1 = hashlib.sha1()

            # chunkwise hashing to not load big files in memory as whole
            chunk_size = 4 * 1024 * 1024  # 4 MiB
            file_obj = fs_handle.open_meta(self.inode)
            offset = 0
            size = self.file_size
            while offset < size:
                to_read = min(chunk_size, size - offset)
                chunk = file_obj.read_random(offset, to_read)

                if not chunk:
                    # some failure
                    break

                sha1.update(chunk)
                offset += len(chunk)

            # TODO: might get partial hashes in case of failure
            self.sha1 = sha1.hexdigest()


    def read(self, size_to_read=None, fs_handle=None):
        '''reads data from the specified file'''
        # last = time.time()
        # thisone = time.time()
        # print('called read()', thisone-last)

        if type(size_to_read) is not int and size_to_read is not None:
            raise TypeError

        if self.file_size == 0:
            return b''

        if fs_handle is None:
            import marple.disk_access
            # last=thisone
            # thisone= time.time()
            # print('import done', thisone-last)

            the_disk_image = marple.disk_access.get_disk_accessor(self.path_to_disk_image)
            # last=thisone
            # thisone= time.time()
            # print('disk accessor open', thisone-last)

            file_system_handles = the_disk_image.get_file_system_handles()
            file_system_handle = file_system_handles[self.partition_sector]

            # last=thisone
            # thisone= time.time()
            # print('fs handles got', thisone-last)
        else:
            file_system_handle = fs_handle

        file_obj = file_system_handle.open_meta(self.inode)  # keeps file pointer open afterward for additional reads

        # last=thisone
        # thisone= time.time()
        # print('fileobj got', thisone-last)

        if size_to_read is None:   # then read all the data
            data = file_obj.read_random(0, self.file_size)  # just read 8 bytes of that file as example
            return data
        else:  # then read what was asked for
            if self.__bytes_read >= self.file_size: # if already over-read the file...
                return b''
            data = file_obj.read_random(self.__bytes_read, size_to_read)  # read from last position, so this works in a loop
            self.__bytes_read = min(self.__bytes_read + size_to_read, self.file_size)

            # last = thisone
            # thisone = time.time()
            # print('data read', thisone-last)
            return data

    def close(self):
        self.file_obj.close()