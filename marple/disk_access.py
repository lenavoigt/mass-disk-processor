import os
from marple.disk_access_raw import RawDiskAccessor
from marple.disk_access_ewf import EwfDiskAccessor

class DiskAccessorError(Exception):
    pass

def get_disk_accessor(path_to_disk_image):
    '''Abstracts away the type of disk image and returns correct subclass of GenericDiskAccesosr
    (EwfDiskAccessor, or RawDiskAccessor'''
    if type(path_to_disk_image) is not str:
        raise TypeError("path_to_disk_image should be a string, not {}".format(type(path_to_disk_image)))
    if not os.path.exists(path_to_disk_image):
        raise FileNotFoundError("Disk image '{}' not found".format(path_to_disk_image))

    f = open(path_to_disk_image, 'rb')
    sector = f.read(512)
    f.close()

    if sector[0:3] == b'EVF':  # is ewf file
        try:
            disk_accessor = EwfDiskAccessor(path_to_disk_image)
        except DiskAccessorError:
            print('Error opening EWF disk image')
            quit()
    else:  # assume raw disk
        try:
            disk_accessor = RawDiskAccessor(path_to_disk_image)
        except DiskAccessorError:
            print('Error opening raw image, or unsupprted image type')
            quit()

    return disk_accessor


