import argparse
import logging
import os.path
import sys
import time
from pathlib import Path

import mdp_lib.disk_image_info
import mdp_lib.mdp_plugin
from config.config import populate_file_signatures, populate_file_hashes_and_signatures
from config.plugin_config import enabled_plugins
from plugin_registry import load_enabled_plugins
from utils.write_to_file import generate_result_file_names, write_single_evidence_results_to_json, \
    write_single_evidence_results_to_tsv, generate_summary_table_dict


def parse_args():
    # --basepath (path to folder containing a lot of evidence/data to process)
    # TODO maybe add alternatives
    # --path (path to disk to process)
    # --output (path for output

    parser = argparse.ArgumentParser()
    parser.add_argument("basepath", type=Path, help="Absolute path to the directory containing all case folders. Each "
                                                    "case must have a 'data' subfolder containing the digital "
                                                    "evidence (i.e. the .dd or .E01, .E02, ... files.")
    args = parser.parse_args()
    if not args.basepath.exists() or not args.basepath.is_dir():
        print("Basepath provided doesn't exist or is not a directory.")
        sys.exit(1)

    return args


def setup_logging(log_filename):
    logging.basicConfig(
        filename=log_filename,
        filemode='a',
        encoding='utf-8',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def initialize_disk_image(each_disk_image: dict[str, str], current_error_summary):
    each_disk_image_path = each_disk_image['path']
    each_disk_image_target_folder = each_disk_image['target_folder']
    each_disk_image_object = None
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

            print('Initializing disk image:', each_disk_image_path)
            print('...', end=' ')

            try:
                each_disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(each_disk_image_path)
                each_disk_image_object.base_path = each_disk_image_target_folder
                print('Initialized')

                if populate_file_hashes_and_signatures:
                    print('Computing file hashes and retrieving file signatures ...')
                    each_disk_image_object.populate_file_hashes_and_signatures()
                elif populate_file_signatures and not populate_file_hashes_and_signatures:
                    print('Retrieving file signatures ...')
                    each_disk_image_object.populate_file_signatures()

                print('File hashes computed: ', populate_file_hashes_and_signatures)
                print('File signatures retrieved: ', populate_file_signatures)
            except Exception as e:
                current_error_summary.append((each_disk_image_path, 'Disk Image Initialization', e))
                print(f'Initialization of Disk Image failed: {each_disk_image_path}: {e}')
        else:
            print('skipping Exx fragment ({}) - handled with E01...'.format(each_disk_image_path))

    return each_disk_image_object


def main():
    start_time = time.time()

    # Command line parameter handling
    args = parse_args()
    path_to_disk_images = args.basepath

    # loading user-specified enabled plugin classes
    plugin_classes = load_enabled_plugins(enabled_plugins)

    # generate file names that include timestamps to avoid overwriting
    json_filename, tsv_filename, log_filename = generate_result_file_names()

    setup_logging(log_filename)
    current_error_summary = []

    disk_images = __get_disk_images_from_path(path_to_disk_images)

    print(
        f"Collecting metrics from {len(plugin_classes)} plugins for disk images in folder: {path_to_disk_images}.")

    # iterate through disk images in target folder and run plugins
    no_disk_images = 0
    for each_disk_image in disk_images:
        each_disk_image_results = []
        each_disk_image_object = initialize_disk_image(each_disk_image, current_error_summary)
        if each_disk_image_object:
            no_disk_images += 1
            for each_plugin in plugin_classes:
                res = process_disk_image(each_disk_image_object, each_plugin)
                if issubclass(type(res), Exception):
                    current_error_summary.append((each_disk_image['path'], each_plugin.name, res))
                else:
                    each_disk_image_results.append(res)
            result_dict = generate_summary_table_dict(each_disk_image_results)
            # write results to json and tsv after each disk image is processed
            write_single_evidence_results_to_json(result_dict, json_filename)
            write_single_evidence_results_to_tsv(result_dict, tsv_filename)

    print('\nFailures ({})'.format(len(current_error_summary)))
    print('================')
    for each_failure in current_error_summary:
        print(each_failure)

    end_time = time.time()
    total_time = end_time - start_time

    print('=' * 20)
    print(f'Processing completed in {(total_time / 60)} minutes for {no_disk_images} disk images.')
    print('=' * 20)


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
        with open(results_file, 'a') as f:
            f.write(str(res) + '\n')

    return res


def __run_plugins(plugin_folder, target_disk_image):
    pass


def __get_disk_images_from_path(target_base_path):
    """returns a list of Disk Image dicts (containing path and target folder)"""
    if not os.path.exists(target_base_path):
        raise FileNotFoundError('Basepath not found')

    all_disk_images = []
    for each_folder in os.listdir(target_base_path):
        try:
            if each_folder != ".DS_Store":  # fix for macos
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
