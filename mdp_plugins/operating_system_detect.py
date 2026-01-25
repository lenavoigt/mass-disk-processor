import re
import plistlib

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class EstimateOS(MDPPlugin):
    name = 'operating_system'
    description = 'Check for OS present'
    expected_results = [
        'windows_found',
        'linux_found',
        'macos_found',
        'ios_backup_found',
        'ios_fs_found',
        'android_found'
    ]

    def _read_file_content(self, file_item, accessor):
        """Read file content using the accessor's file system handles."""
        try:
            fs_handles = accessor.get_file_system_handles()
            fs_handle = fs_handles.get(file_item.partition_sector)
            return file_item.read(fs_handle=fs_handle)
        except Exception:
            return None

    def _check_system_version_plist(self, file_item, accessor):
        """
        Read SystemVersion.plist and determine if it's macOS or iOS.

        Returns: 'macos', 'ios', or None
        """
        try:
            content = self._read_file_content(file_item, accessor)
            if content:
                plist = plistlib.loads(content)
                product_name = plist.get('ProductName', '')

                # iOS variants: "iPhone OS", "iOS"
                if 'iPhone' in product_name or product_name == 'iOS':
                    return 'ios'
                # macOS variants: "Mac OS X", "macOS"
                elif 'Mac' in product_name or 'macOS' in product_name:
                    return 'macos'
        except Exception:
            pass
        return None

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        win_found = False
        lin_found = False
        macos_found = False
        ios_backup_found = False
        ios_fs_found = False
        android_found = False

        system_version_file = None

        # First pass: detect OS indicators by file paths
        for each_file in files:
            path = each_file.full_path

            # Windows: Registry hive
            if re.search(r'Windows/System32/config/software$', path, re.IGNORECASE):
                win_found = True

            # Apple SystemVersion.plist - save for later content check
            if re.search(r'System/Library/CoreServices/SystemVersion\.plist$', path, re.IGNORECASE):
                system_version_file = each_file

            # iOS Backup structure (from iTunes/Finder backups)
            if re.search(r'HomeDomain/', path, re.IGNORECASE):
                ios_backup_found = True

            # iOS Full Filesystem indicators (not in macOS)
            if re.search(r'private/var/mobile/', path, re.IGNORECASE):
                ios_fs_found = True
            if re.search(r'MobileAsset/Assets/', path, re.IGNORECASE):
                ios_fs_found = True

            # Android indicators
            if re.search(r'data/misc/bluedroid/', path, re.IGNORECASE):
                android_found = True
            if re.search(r'data/system/users/\d+/registered_services/', path, re.IGNORECASE):
                android_found = True
            if re.search(r'data/data/com\.android\.', path, re.IGNORECASE):
                android_found = True

            # Linux indicators (but not if Android is found)
            if re.search(r'/etc/os-release$', path, re.IGNORECASE):
                lin_found = True
            if re.search(r'var/log/syslog$', path, re.IGNORECASE):
                lin_found = True

        # Second pass: read SystemVersion.plist to distinguish macOS from iOS
        if system_version_file and not ios_fs_found:
            os_type = self._check_system_version_plist(system_version_file, disk_image)
            if os_type == 'macos':
                macos_found = True
            elif os_type == 'ios':
                ios_fs_found = True
        elif system_version_file and ios_fs_found:
            # Already detected as iOS via file paths, just confirm
            macos_found = False

        # If Android is found, don't report Linux (Android is Linux-based but distinct)
        if android_found:
            lin_found = False

        result = self.create_result(target_disk_image)
        self.set_results(result, {
            'windows_found': str(win_found),
            'linux_found': str(lin_found),
            'macos_found': str(macos_found),
            'ios_backup_found': str(ios_backup_found),
            'ios_fs_found': str(ios_fs_found),
            'android_found': str(android_found)
        })

        return result
