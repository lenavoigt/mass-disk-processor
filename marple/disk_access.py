import os
import logging
from marple.disk_access_raw import RawDiskAccessor
from marple.disk_access_ewf import EwfDiskAccessor
from marple.disk_access_ios_backup import iOSBackupAccessor, is_ios_backup, iOSBackupError
from marple.disk_access_tar import TarAccessor, is_tar_archive, TarAccessorError
from marple.disk_access_zip import ZipAccessor, is_zip_archive, ZipAccessorError

class DiskAccessorError(Exception):
    pass

def get_disk_accessor(path_to_disk_image):
    '''Abstracts away the type of disk image and returns correct subclass of GenericDiskAccessor
    (EwfDiskAccessor, RawDiskAccessor, or iOSBackupAccessor)'''
    if type(path_to_disk_image) is not str:
        raise TypeError("path_to_disk_image should be a string, not {}".format(type(path_to_disk_image)))
    if not os.path.exists(path_to_disk_image):
        raise FileNotFoundError("Disk image '{}' not found".format(path_to_disk_image))

    # Check if this is an iOS backup directory
    if is_ios_backup(path_to_disk_image):
        try:
            disk_accessor = iOSBackupAccessor(path_to_disk_image)
            return disk_accessor
        except iOSBackupError as e:
            logging.warning(f"Could not open iOS backup: {e}")
            raise DiskAccessorError(f"iOS backup error: {e}")

    # For file-based disk images
    if not os.path.isfile(path_to_disk_image):
        raise DiskAccessorError(f"Path is not a file or iOS backup: {path_to_disk_image}")

    # Check if this is a tar archive (by extension)
    if is_tar_archive(path_to_disk_image):
        try:
            disk_accessor = TarAccessor(path_to_disk_image)
            return disk_accessor
        except TarAccessorError as e:
            logging.warning(f"Could not open tar archive: {e}")
            raise DiskAccessorError(f"Tar archive error: {e}")

    # Check if this is a zip archive (by extension)
    if is_zip_archive(path_to_disk_image):
        try:
            disk_accessor = ZipAccessor(path_to_disk_image)
            return disk_accessor
        except ZipAccessorError as e:
            logging.warning(f"Could not open zip archive: {e}")
            raise DiskAccessorError(f"Zip archive error: {e}")

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
            print('Error opening raw image, or unsupported image type')
            quit()

    return disk_accessor


