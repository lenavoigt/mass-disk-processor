from typing import List

# General
from mdp_plugins import (
    disk_size,
    disk_image_lifespan,
    no_files,
    no_partitions,
    no_partition_types,
    num_user_files,
    operating_system_detect,
    file_size_stats,
    file_types
)

# Browser history
from mdp_plugins import (
    chrome_history,
    edge_history,
    firefox_history
)

# Windows-specific
from mdp_plugins import (
    win_apps,
    win_browsers,
    win_computer_and_user_names,
    win_evt_logins,
    win_lifespan,
    win_num_prefetch_files,
    win_num_usbs,
    win_num_user_lnk_files,
    win_num_wifi_connections,
    win_screen_resolution,
    win_user_info,
    win_version
)

# External
from mdp_plugins import (
    external_program_demo,
    plaso
)

plugin_registry = {
    # General
    "disk_size": disk_size.DiskSize,
    "no_partitions": no_partitions.NumberOfPartitions,
    "no_partition_types": no_partition_types.NumberOfPartitionTypes,
    "no_files": no_files.NumberOfFiles,
    "num_user_files": num_user_files.NumberOfUserFiles,
    "file_types": file_types.FileTypes,
    "file_size_stats": file_size_stats.FileSizeStats,
    "disk_image_lifespan": disk_image_lifespan.Lifespan,
    "operating_system_detect": operating_system_detect.EstimateOS,

    # Browser history
    "firefox_history": firefox_history.FirefoxHistory,
    "chrome_history": chrome_history.ChromeHistory,
    "edge_history": edge_history.EdgeHistory,

    # Windows
    "win_lifespan": win_lifespan.WinOSLifespan,
    "win_version": win_version.WinVersion,
    "win_user_info": win_user_info.UserInfo,
    "win_computer_and_user_names": win_computer_and_user_names.WinComputerAndUserName,
    "win_screen_resolution": win_screen_resolution.WinScreenResolution,
    "win_evt_logins": win_evt_logins.EVTXLogs,
    "win_apps": win_apps.WinApps,
    "win_browsers": win_browsers.WinBrowsers,
    "win_num_user_lnk_files": win_num_user_lnk_files.WinNumberOfUserLNKFiles,
    "win_num_prefetch_files": win_num_prefetch_files.WinNumberOfPrefetchFiles,
    "win_num_usbs": win_num_usbs.WinUSBCount,
    "win_num_wifi_connections": win_num_wifi_connections.WinWifiCount,

    # External
    "external_program_demo": external_program_demo.ExternalProgramDemo,
    "plaso": plaso.Plaso
}

def load_enabled_plugins(enabled_plugins: List[str]):
    plugins = []

    for name in enabled_plugins:
        plugin_class = plugin_registry.get(name)
        if plugin_class:
            plugins.append(plugin_class())
        else:
            print(f"Plugin not found in registry: {name} \nSkipping...")

    return plugins