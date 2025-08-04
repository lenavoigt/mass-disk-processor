import csv
import json
import os
from datetime import datetime
from typing import List

from mdp_lib.plugin_result import MDPResult


def generate_result_file_names():
    os.makedirs('output', exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    json_filename = f"output/summary_dict_{timestamp}.json"
    tsv_filename = f"output/data_table_{timestamp}.tsv"
    return json_filename, tsv_filename, f"output/{timestamp}.log"


def generate_summary_table_dict(result_list: List[MDPResult]):
    # generate summary table dictionary

    output_dict = {}

    for each_result in result_list:
        if each_result.include_in_data_table:
            if each_result.source_file not in output_dict:
                output_dict[each_result.source_file] = {}

            for each_plugin in each_result.results:
                output_dict[each_result.source_file][each_plugin] = {'plugin_name': each_result.plugin, 'result_value': each_result.results[each_plugin]}

    return output_dict


def write_single_evidence_results_to_json(result_list: dict, json_file_name: str):
    print(f'    Writing output to {json_file_name}')
    single_evidence_json_dump = json.dumps(result_list)

    with open(json_file_name, "a") as f:
        f.write(single_evidence_json_dump + "\n")


def write_single_evidence_results_to_tsv(single_result_dict: dict, tsv_file_name: str):
    print(f'\tWriting summary data table to {tsv_file_name}.')

    disk_image_path, result_data = next(iter(single_result_dict.items()))

    new_row = {'disk_image': disk_image_path}
    for key, plugin_output in result_data.items():
        new_row[key] = plugin_output.get('result_value')

    # first time write to tsv, create new with headers
    if not os.path.exists(tsv_file_name):
        fieldnames = list(new_row.keys())
        with open(tsv_file_name, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', restval='')
            writer.writeheader()
            writer.writerow(new_row)
        return

    # File exists -> read existing data and headers
    with open(tsv_file_name, 'r', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        existing_rows = list(reader)
        fieldnames = reader.fieldnames or []

    # check if current result list has additional plugin results compared to existing colums in tsv
    existing_headers = set(fieldnames)
    new_row_headers = set(new_row.keys())

    # no new headers -> write to existing tsv
    if new_row_headers.issubset(existing_headers):
        with open(tsv_file_name, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', restval='')
            writer.writerow(new_row)
            return

    # Add new headers as new colums at the end
    for field in new_row:
        if field not in fieldnames:
            fieldnames.append(field)

    # Ensure disk_image column stays first
    if 'disk_image' in fieldnames:
        fieldnames.remove('disk_image')
    fieldnames = ['disk_image'] + fieldnames

    # Rewrite file with updated fieldnames
    with open(tsv_file_name, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', restval='')
        writer.writeheader()
        for row in existing_rows:
            writer.writerow(row)
        writer.writerow(new_row)

