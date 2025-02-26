import sqlite3
import os
import time
from typing import List

from marple.file_object import FileItem

import mdp_lib.plugin_result
from mdp_lib.config import path_to_nsrl
from mdp_lib.disk_image_info import TargetDiskImage


class NumberOfFiles(object):
    name = 'no_files'
    description = 'Number of files'
    include_in_data_table = True


    @staticmethod
    def is_sha1_in_nsrl(sha1, conn) -> bool:
        # print(sha1.upper())
        cursor = conn.cursor()

        # noinspection SqlResolve, SqlNoDataSourceInspection
        # Debugging: check id index is used
        # query_plan = """EXPLAIN QUERY PLAN SELECT sha1 FROM FILE WHERE sha1 = ?"""
        # cursor.execute(query_plan, (sha1.upper(),))
        # plan = cursor.fetchall()
        # print("Query Plan:", plan)

        query = """SELECT EXISTS(SELECT 1 FROM FILE WHERE sha1 = ?)"""

        # print('running nsrl query...', end=' ')
        # nsrl_start = time.time()

        cursor.execute(query, (sha1.upper(),))
        result = cursor.fetchone()[0]

        # nsrl_end = time.time()
        # print('query complete in {} seconds'.format(nsrl_end-nsrl_start))

        cursor.close()

        return bool(result)

    def process_disk(self, target_disk_image: TargetDiskImage):

        disk_image = target_disk_image.accessor
        files = disk_image.files
        no_files = len(files)
        # print('no_files: {}'.format(no_files))
        no_non_nsrl_files = None
        # no_nsrl = None
        # no_nsrl_non_zero = None
        no_non_nsrl_files_incl_zero = None

        hashes_populated = target_disk_image.attributes['hashes_populated']

        if hashes_populated and path_to_nsrl:
            # TODO exception handling for incorrect path_to_nsrl or unexpected nsrl db
            # need sth like check whether nsrl db is valid, only go here if nsrl check method if valid

            if not os.path.exists(path_to_nsrl):
                print('Provided NSRL database does not exist, skipping NSRL lookups')
            else:
                print('NSRL database found...')

                # open database here once
                open_db_start = time.time()
                conn = sqlite3.connect(path_to_nsrl)
                open_db_end = time.time()
                print('NSRL database opened in {} seconds'.format(open_db_end-open_db_start))

                no_non_nsrl_files = 0
                no_non_nsrl_files_incl_zero = 0
                no_nsrl = 0
                no_nsrl_non_zero = 0
                files: List[FileItem] = disk_image.files
                for each_file in files:
                    sha1_file_hash = each_file.sha1
                    if sha1_file_hash:  # field might not populated for larger files (above defined max for hashing)
                        sha1_in_nsrl = self.is_sha1_in_nsrl(sha1_file_hash, conn)
                        if sha1_in_nsrl:
                            no_nsrl += 1
                            if each_file.file_size > 0:
                                no_nsrl_non_zero += 1
                            else:
                                no_non_nsrl_files_incl_zero += 1
                        else:
                            no_non_nsrl_files += 1
                            no_non_nsrl_files_incl_zero += 1
                    else:
                        #print('Unknown whether NSRL:', each_file.full_path)
                        no_non_nsrl_files += 1
                        no_non_nsrl_files_incl_zero += 1

                # close database here
                conn.close()
                # print('NSRL database check took {} seconds'.format(time.time()-open_db_start))

                # print("NSRL: ", no_nsrl)
                # print("NSRL/Zero: ", no_nsrl_non_zero)
        else:
            print('File hash fields not populated. Skipping NSRL RDS check.')

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results['no_files'] = no_files
        res.results['no_non_nsrl_files'] =  no_non_nsrl_files
        res.results['no_non_nsrl_files_incl_zero'] = no_non_nsrl_files_incl_zero
        # res.results['no_nsrl'] = no_nsrl
        # res.results['no_nsrl_non_zero'] = no_nsrl_non_zero

        return res
