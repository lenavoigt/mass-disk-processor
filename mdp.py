import argparse
import os.path
import csv
import json
import logging
import time

import mdp_lib.disk_image_info
import mdp_lib.plugin_result
import mdp_lib.plugin_order_config

# Add plugin imports here

import mdp_plugins.external_program_demo
import mdp_plugins.disk_image_lifespan
import mdp_plugins.disk_size
import mdp_plugins.no_files
import mdp_plugins.no_partitions
import mdp_plugins.num_user_files
import mdp_plugins.win_num_user_lnk_files
import mdp_plugins.operating_system_detect
import mdp_plugins.plaso
import mdp_plugins.win_lifespan
import mdp_plugins.win_num_usbs
import mdp_plugins.win_user_info
import mdp_plugins.win_num_prefetch_files
import mdp_plugins.win_screen_resolution
import mdp_plugins.win_version
import mdp_plugins.win_evt_logins
import mdp_plugins.win_browsers
import mdp_plugins.win_apps
import mdp_plugins.file_types
import mdp_plugins.firefox_history
import mdp_plugins.chrome_history
import mdp_plugins.edge_history
import mdp_plugins.file_size_stats
import mdp_plugins.win_computer_and_user_names
import mdp_plugins.win_num_wifi_connections

from mdp_lib.config import populate_file_signatures, populate_file_hashes_and_signatures

def main():

    start_time = time.time()
    disk_images_processed = 0

    # --path (path to disk to process) #TODO
    # --basepath (path to folder containing a lot of evidence/data to process)
    # --ouptut (path for output) # todo

    # Command line parameter handling
    parser = argparse.ArgumentParser()
    parser.add_argument("basepath")
    args = parser.parse_args()
    path_to_disk_images = args.basepath

    # add methods from plugins to call here
    plugin_classes = [
                      mdp_plugins.disk_size.DiskSize(),
                      mdp_plugins.no_partitions.NumberOfPartitions(),
                      mdp_plugins.disk_image_lifespan.Lifespan(),
                      mdp_plugins.no_files.NumberOfFiles(),
                      mdp_plugins.num_user_files.NumberOfUserFiles(),
                      mdp_plugins.file_types.FileTypes(),
                      mdp_plugins.operating_system_detect.EstimateOS(),

                      mdp_plugins.win_lifespan.WinOSLifespan(),
                      mdp_plugins.win_version.WinVersion(),
                      mdp_plugins.win_user_info.UserInfo(),

                      mdp_plugins.win_evt_logins.EVTXLogs(),

                      mdp_plugins.win_screen_resolution.WinScreenResolution(),
                      mdp_plugins.win_apps.WinApps(),

                      mdp_plugins.win_num_user_lnk_files.WinNumberOfUserLNKFiles(),
                      mdp_plugins.win_num_prefetch_files.WinNumberOfPrefetchFiles(),
                      mdp_plugins.win_num_usbs.WinUSBCount(),

                      mdp_plugins.win_browsers.WinBrowsers(),
                      mdp_plugins.firefox_history.FirefoxHistory(),
                      mdp_plugins.chrome_history.ChromeHistory(),
                      mdp_plugins.edge_history.EdgeHistory(),

                      mdp_plugins.file_size_stats.FileSizeStats(),
                      mdp_plugins.win_num_usbs.WinUSBCount(),
                      mdp_plugins.win_computer_and_user_names.WinComputerAndUserName(),
                      mdp_plugins.win_num_wifi_connections.WinWifiCount(),
                      # mdp_plugins.plaso.Plaso(),
                      # mdp_plugins.external_program_demo.ExternalProgramDemo(),
                      ]

    logging.basicConfig(filename='log.txt', encoding='utf-8')

    result_list = process_multiple_disk_images(path_to_disk_images, plugin_classes)

    summary_dict = generate_summary_table_dict(result_list)

    f = open('summary_dict.json', 'w')
    f.write(json.dumps(summary_dict))
    f.close()

    write_summary_to_disk(summary_dict, 'data_table.tsv')

    end_time = time.time()
    total_time = end_time - start_time

    print('='*20)
    print('Processing complete for {} disk images in {} minutes.'.format(len(summary_dict), total_time/60))
    print('='*20)




def generate_summary_table_dict(result_list):
    # generate summary table dictionary

    plugin_order = mdp_lib.plugin_order_config.plugin_order

    out = {}

    for each_result in result_list:
        if each_result.include_in_data_table:
            if each_result.source_file not in out:
                out[each_result.source_file] = {}

            for each_plugin in each_result.results:
                out[each_result.source_file][each_plugin] = {'plugin_name': each_result.plugin, 'result_value': each_result.results[each_plugin]}

    sorted_out = {}

    # IDEA: Plugin ordering in final result output:
    # Order of plugin classes:
    # - Plugins are ordered by the name of their plugin class (e.g. 'file_types'), .
    # - If this plugin name occurs in the plugin order config, they are ordered in accordance with this config.
    # - All results of plugins, where the plugin name is not in the config, are appended at the end of the output. Ordered alphabetically by plugin name.
    # Order within plugin classes:
    # - Results of the same plugin class (and therefore with the same plugin name) are ordered alphabetically by their result value name (e.g. in class 'file_types': 'audio_files, 'compressed_files', ...)

    for case in out:
        results = out[case]
        sorted_out_case = {}

        # add values based on the provided plugin order
        for plugin_name in plugin_order:
            plugin_results = {}
            for result_name in results:
                result_value = results[result_name]
                if result_value['plugin_name'] == plugin_name:
                    plugin_results[result_name] = result_value['result_value']

            # Sort values alphabetically for the same plugin name
            for result_name in sorted(plugin_results.keys()):
                sorted_out_case[result_name] = plugin_results[result_name]

        # if there are plugins that are not in the plugin order
        # they are appended at the end in alphabetical order (of plugin name)

        extra_plugins = {}

        for result_name in results:
            result_value = results[result_name]
            plugin_name = result_value['plugin_name']
            if plugin_name not in plugin_order:
                # checking if we already have this plugin name in our extra plugin list
                if plugin_name not in extra_plugins:
                    extra_plugins[plugin_name] = {}
                extra_plugins[plugin_name][result_name] = result_value['result_value']

        # Sort the extra plugins alphabetically by plugin name and then by plugin value name
        for plugin_name in sorted(extra_plugins.keys()):
            for result_name in sorted(extra_plugins[plugin_name].keys()):
                sorted_out_case[result_name] = extra_plugins[plugin_name][result_name]

        sorted_out[case] = sorted_out_case

    return sorted_out

def write_summary_to_disk(summary_dict, filename):
    print('Writing summary tsv to disk...')
    # first_key = next(iter(summary_dict))
    fields = ['category', 'disk_image',]
    additional_fields = []

    for each_result in summary_dict:
        for each_field in summary_dict[each_result]:
            if each_field not in fields and each_field not in additional_fields:
                # print('added field {}'.format(each_field))
                additional_fields.append(each_field)

    # additional_fields.sort()
    fields.extend(additional_fields)

    #fields.extend(list(summary_dict[first_key].keys()))
    #print(fields)

    with open(filename, 'w') as csvfile:
        w = csv.DictWriter(csvfile, delimiter='\t', fieldnames=fields, restval='')
        w.writeheader()
        for key, val in sorted(summary_dict.items()):
            #try:
            row = {'disk_image': key}
            row.update(val)
            w.writerow(row)
            # except ValueError:
            #     print('Value error with {} on {}'.format(key, val))


def process_disk_image(disk_image_obj, plugin):
    """runs a single plugin on a single disk image"""
    try:
        print('- running {} ({})'.format(plugin.name, plugin.description))
        res = plugin.process_disk(disk_image_obj)
    except Exception as e:
        print("FAILED TO PROCESS {} ({})".format(disk_image_obj.image_path, e))
        return e

    if plugin.include_in_data_table:
        res.include_in_data_table = True

    results_folder = disk_image_obj.results_path
    os.makedirs(results_folder, exist_ok=True)

    results_file = os.path.join(results_folder, 'results_' + plugin.name + '.txt')

    if True:  # replace with option to write results at some point
        f = open(results_file, 'a')
        f.write(str(res) + '\n')
        f.close()

    return res

def process_multiple_disk_images(base_path_to_images, plugins):
    """runs a list of plugins on multiple disk images"""
    list_of_results = []

    failures = []

    disk_images = __get_disk_images_from_path(base_path_to_images)
    # timelog_file_path = "timelog.txt"

    for each_disk_image in disk_images:
        each_disk_image_path = each_disk_image['path']
        each_disk_image_target_folder = each_disk_image['target_folder']
        if not each_disk_image_path.endswith('.DS_Store'):  # mac os necessity

            if each_disk_image_path[-3:] not in ['E02', 'E03', 'E04', 'E05', 'E06', 'E07', 'E08', 'E09', 'E10',
                                                 'E11', 'E12', 'E13', 'E14', 'E15', 'E16', 'E17', 'E18', 'E19', 'E20',
                                                 'E21', 'E22', 'E23', 'E24', 'E25', 'E26', 'E27', 'E28', 'E29', 'E30',
                                                 'E31', 'E32', 'E33', 'E34', 'E35', 'E36', 'E37', 'E38', 'E39', 'E40',
                                                 'E41', 'E42', 'E43', 'E44', 'E45', 'E46', 'E47', 'E48', 'E49', 'E50',
                                                 'E51', 'E52', 'E53', 'E54', 'E55', 'E56', 'E57', 'E58', 'E59', 'E60',
                                                 'E61', 'E62', 'E63', 'E64', 'E65', 'E66', 'E67', 'E68', 'E69', 'E70',
                                                 'E71', 'E72', 'E73', 'E74', 'E75', 'E76', 'E77', 'E78', 'E79', 'E80',
                                                 'E81', 'E82', 'E83', 'E84', 'E85', 'E86', 'E87', 'E88', 'E89', 'E90',
                                                 'E91', 'E92', 'E93', 'E94', 'E95', 'E96', 'E97', 'E98', 'E99']:
                print('=============================================')
                print('processing {}...'.format(each_disk_image_path))
                print('=============================================')
                # start_time = time.time()
                # start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))

                ######

                print('Initializing disk image:', each_disk_image_path)
                print('...', end=' ')

                # start_time = time.time()
                # start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))

                try:
                    each_disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(each_disk_image_path)
                    each_disk_image_object.base_path = each_disk_image_target_folder
                    print('Initialized')

                    if populate_file_hashes_and_signatures:
                        print('Computing file hashes and retrieving file signatures ...')
                        each_disk_image_object.populate_file_hashes_and_signatures()
                    elif populate_file_signatures and not populate_file_hashes_and_signatures:
                        # start_time_p = time.time()
                        print('Retrieving file signatures ...')
                        each_disk_image_object.populate_file_signatures()
                        # end_time_p = time.time()
                        # print('File signature population took: ', end_time_p - start_time_p)

                    print('File hashes computed: ', populate_file_hashes_and_signatures)
                    print('File signatures retrieved: ', populate_file_signatures)

                    # for each_file in each_disk_image_object.files:
                    #     print(each_file.to_dict())

                    for each_plugin in plugins:
                        res = process_disk_image(each_disk_image_object, each_plugin)
                        if issubclass(type(res), Exception):
                            failures.append((each_disk_image_path, each_plugin.name, res))
                        else:
                            list_of_results.append(res)

                    # end_time = time.time()
                    # end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
                    #
                    # total_time = end_time - start_time
                    # with open(timelog_file_path, "a") as timelog_file:
                    #     timelog_file.write("=" * 40 + "\n")
                    #     timelog_file.write("Processing:")
                    #     timelog_file.write(f"Disk Image Path: {each_disk_image_path}\n")
                    #     timelog_file.write("=" * 40 + "\n")
                    #     timelog_file.write(f"Start Time: {start_time_str}\n")
                    #     timelog_file.write(f"End Time: {end_time_str}\n")
                    #     timelog_file.write(f"Total Time: {total_time:.2f} seconds\n")
                    #     timelog_file.write("=" * 40 + "\n\n")
                except Exception as e:
                    failures.append((each_disk_image_path, 'Disk Image Initialization', e))
                    print(f'Initialization of Disk Image failed: {each_disk_image_path}: {e}')
            else:
                print('skipping Exx fragment ({}) - handled with E01...'.format(each_disk_image_path))

    print('\nFailures ({})'.format(len(failures)))
    print('================')
    for each in failures:
        print(each)

    return list_of_results









def __run_plugins(plugin_folder, target_disk_image):
    pass

def __get_disk_images_from_path(target_base_path):
    """returns a list of Disk Image dicts (containing path and target folder)"""
    if not os.path.exists(target_base_path):
        raise FileNotFoundError('Basepath not found')

    all_disk_images = []
    for each_folder in os.listdir(target_base_path):
        try:
            if each_folder != ".DS_Store": # fix for macos
                disk_images = __get_disk_images_from_sub_folder(os.path.join(target_base_path, each_folder))
                all_disk_images.extend(disk_images)
        except FileNotFoundError as e:
            logging.error(e)
    return all_disk_images

def __get_disk_images_from_sub_folder(target_folder):
    """return dict of disk image and target folder paths, for a folder of structure:
        case1
            data
        case2
            data

            etc.
    """
    data_path = os.path.join(target_folder, 'data')
    if not os.path.exists(data_path):
        raise FileNotFoundError('No data folder in case path ({})'.format(target_folder))

    disk_images = []
    for each_disk_image_file in os.listdir(data_path):
        disk_images.append({'path': os.path.join(data_path, each_disk_image_file), 'target_folder': target_folder})

    return disk_images



if __name__ == '__main__':
    main()

