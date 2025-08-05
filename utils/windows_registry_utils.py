import io
import re

from typing import Optional, Any, List

from Registry import Registry

from marple.file_object import FileItem


def _load_registry_from_file(file_obj: bytes) -> Optional[Registry.Registry]:
    """
    Loads a Registry hive from a bytes object.
    """
    try:
        return Registry.Registry(io.BytesIO(file_obj))
    except Exception as e:
        print(f"Error loading registry: {e}")
        return None


def _get_hive_pattern(hive_name: str) -> Optional[re.Pattern]:
    """
    Returns a (compiled) regex pattern to match the full path of the given registry hive.
    """
    patterns = {
        "SOFTWARE": r'windows/system32/config/software$',
        "SYSTEM": r'windows/system32/config/system$',
        "SAM": r'windows/system32/config/sam$',
        "NTUSER": r'Users/.+/NTUSER\.DAT$',
        # "SECURITY": r'windows/system32/config/security$',
        # "DEFAULT": r'windows/system32/config/default$',
        # "USRCLASS": r'/usrclass\.dat$',
    }
    pattern = patterns.get(hive_name.upper())
    return re.compile(pattern, re.IGNORECASE) if pattern else None


def get_current_control_set_number(files: List[FileItem]) -> Optional[int]:
    """
    Gets the current control set number.

    Example usage in win_computer_and_user_names.py -> ccs for computername retrieval determined via this helper
    """
    val = get_registry_value(files, "SYSTEM", "Select", "Current")
    return val if isinstance(val, int) else None


def get_registry_value(files: List[FileItem], hive_name: str, key_path: str, value_name: str) -> Optional[Any]:
    """
    Given the list of files from the disk image accessor of a traget disk image,
    finds the specified registry hive, opens the key, and returns the value.

    Example usage in win_lifespan.py -> install_time value retrieved via this helper
    """

    pattern = _get_hive_pattern(hive_name)

    if not pattern:
        print(f"Unknown (or not yet in util implemented) registry hive name: {hive_name}")
        return None

    for file in files:
        if pattern.search(file.full_path.lower()):
            reg = _load_registry_from_file(file.read())
            if not reg:
                continue
            try:
                key = reg.open(key_path)
                return key.value(value_name).value()
            except Registry.RegistryKeyNotFoundException:
                print(f"Registry key not found: {key_path}")
            except Registry.RegistryValueNotFoundException:
                print(f"Registry value not found: {value_name}")
            except Exception as e:
                print(f"Error reading registry value: {e}")
    return None


def count_registry_subkeys(files: List[FileItem], hive_name: str, key_path: str) -> Optional[int]:
    """
    Counts the number of subkeys under the given registry key within the specified hive.

    Example usage in win_num_wifi_connections.py -> wifi_profile_count value retrieved via this helper
    """
    pattern = _get_hive_pattern(hive_name)

    if not pattern:
        print(f"Unknown registry hive name: {hive_name}")
        return None

    for file in files:
        if pattern.search(file.full_path.lower()):
            reg = _load_registry_from_file(file.read())
            if not reg:
                continue
            try:
                key = reg.open(key_path)
                return len(key.subkeys())
            except Registry.RegistryKeyNotFoundException:
                print(f"Registry key not found: {key_path}")
            except Exception as e:
                print(f"Error counting subkeys: {e}")
    return None


def list_registry_subkey_names(files: List[FileItem], hive_name: str, key_path: str) -> Optional[list[str]]:
    """"
    Retrieves the names of all immediate subkeys under a specified registry key within a given registry hive.

    Example usage in win_computer_and_user_names.py -> usernames retrieved via this helper
    """
    pattern = _get_hive_pattern(hive_name)
    if not pattern:
        return None

    for file in files:
        if pattern.search(file.full_path.lower()):
            reg = _load_registry_from_file(file.read())
            if not reg:
                continue
            try:
                key = reg.open(key_path)
                return [subkey.name() for subkey in key.subkeys()]
            except Exception as e:
                print(f"Error listing subkeys: {e}")
    return None

# def list_registry_values(files: List[FileItem], hive_name: str, key_path: str) -> Optional[dict[str, Any]]:
#     """
#     Returns all value_name-value_value pairs under a specified registry key in the given reg hive.
#     """
#     pattern = _get_hive_pattern(hive_name)
#
#     if not pattern:
#         print(f"Unknown hive name: {hive_name}")
#         return None
#
#     for file in files:
#         if pattern.search(file.full_path.lower()):
#             reg = _load_registry_from_file(file.read())
#             if not reg:
#                 continue
#             try:
#                 key = reg.open(key_path)
#                 return {val.name(): val.value() for val in key.values()}
#             except Registry.RegistryKeyNotFoundException:
#                 print(f"Registry key not found: {key_path}")
#             except Exception as e:
#                 print(f"Error listing registry values: {e}")
#     return None

