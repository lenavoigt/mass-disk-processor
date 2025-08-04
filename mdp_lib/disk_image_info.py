import os
import time
import sqlite3
import shutil

from typing import List

import marple.disk_access
from marple.file_object import FileItem
from config.config import use_db_for_file_lists, max_file_size_for_sha1_calculation


class TargetDiskImage(object):

    def __init__(self, path_to_disk_image):
        # Class definition as provided earlier
        if not os.path.exists(path_to_disk_image):
            raise FileNotFoundError

        self._disk_image_path = path_to_disk_image

        try:
            self._disk_accessor = marple.disk_access.get_disk_accessor(self._disk_image_path)
        except Exception as e:
            raise RuntimeError(f"Disk access failed: {e}")

        try:
            self._files: List[FileItem]| None = self._disk_accessor.get_list_of_files([])
        except Exception as e:
            raise RuntimeError(f"Population of file list failed for {path_to_disk_image}: {e}")

        self.base_path = ''

        self._attributes = {}

        self.add_attributes('hashes_populated', False)
        self.add_attributes('signatures_populated', False)

        self.results = {}


    @property
    def image_path(self):
        return self._disk_image_path

    @property
    def accessor(self):
        return self._disk_accessor

    @property
    def files(self):
        return self._files.copy()

    @property
    def attributes(self):
        return self._attributes.copy()

    @property
    def results_path(self):
        return os.path.join(self.base_path, 'results')

    def add_attributes(self, key, value):
        self._attributes[key] = value

    def populate_file_signatures(self):
        disk_accessor = self._disk_accessor
        fs_handles = disk_accessor.get_file_system_handles()

        if self._files and not self._attributes['signatures_populated']:
            for each_file in self._files:
                fs_handle = fs_handles[each_file.partition_sector]
                each_file.populate_signature_field(fs_handle=fs_handle)
            self.add_attributes('signatures_populated', True)

    def populate_file_hashes_and_signatures(self):

        if not use_db_for_file_lists and self._attributes['hashes_populated']:
            print('File hashes are populated. Continuing.')
            return

        db_name = f"{os.path.splitext(os.path.basename(self.image_path))[0]}.db"
        db_path = os.path.join(os.path.dirname(os.path.dirname(self.image_path)), db_name)

        # we should not use file db
        if not use_db_for_file_lists:
            if os.path.exists(db_path):
                print('File list database exists but should not be used.')
                self._remove_and_save_existing_db_file(db_path)
            self._populate_file_hash_and_signature_fields_without_db()
            return

        # we should use file db

        disk_accessor = self._disk_accessor
        fs_handles = disk_accessor.get_file_system_handles()

        # 1. Does a db file exist?

        # db does not exist yet
        if not os.path.exists(db_path):
            self._create_and_update_db_file(db_path)
            return

        # db file exists
        print(f'File list database found at {db_path}.')
        # 2. check if expected table layout

        # unexpected table layout -> sth is wrong: create new
        if not self._is_file_table_layout_as_expected(db_path):
            print('Unexpected table layout for file list database.')
            self._remove_and_save_existing_db_file(db_path)
            self._create_and_update_db_file(db_path)
            return

        # expected table layout

        # 3. check if entry for each file in disk images file list

        # not every file in file list has an entry (yet) -> add missing entries
        # TODO currently assumption that db is not fully populated but no "wrong" data, i.e. files that arent on the disk image, file duplicated in db

        print(f'{len(self._files)} files expected in file list database.')

        missing_files = self._files_not_in_db_file_list(db_path)
        print(f'{len(missing_files)} files missing in existing file list database.')
        if len(missing_files) > 0:
            print(f'Populating file signatures and hashes for missing files.')
            # first, populate sha1 and signature fields of files in disk image object's file list for files that already exist in db
            self._update_file_list_sha1_and_signature_from_db(db_path)
            # second, populate sha1 and signature fields for missing files and add to db
            for each_file in missing_files:
                fs_handle = fs_handles[each_file.partition_sector]
                each_file.populate_hash_and_signature_field(hash_size_limit=max_file_size_for_sha1_calculation,
                                                            fs_handle=fs_handle)
                file_db_entry = each_file.to_dict()
                self._add_entry_to_db(db_path, file_db_entry)
            self.add_attributes('hashes_populated', True)
            self.add_attributes('signatures_populated', True)
            # return -> files might be missing AND existing not populated correctly

        # every file in file list has an entry

        # 4. check if field sha1 is populated for all files <= max_file_size, check if field signature is populated for all files

        # sha1 and signature fields not populated as expected
        # TODO Currently not checking if larger files than expected have sha1 value
        unpopulated_files = self._files_sha1_and_signature_not_populated_as_expected(db_path)
        print(f'{len(unpopulated_files)} files in existing file list database with unpopulated file signature and/or hash where hash was expected.')

        if len(unpopulated_files) > 0:
            print(f'Populating file signatures and hashes for unpopulated files.')
            # first, populate sha1 and signature fields of files in disk image object's file list for files that already exist in db
            self._update_file_list_sha1_and_signature_from_db(db_path)
            # second, populate sha1 and signature fields for missing files and add to db
            for each_file in unpopulated_files:
                fs_handle = fs_handles[each_file.partition_sector]
                each_file.populate_hash_and_signature_field(hash_size_limit=max_file_size_for_sha1_calculation,fs_handle=fs_handle)
                file_db_entry = each_file.to_dict()
                self._update_values_of_entry_in_db(db_path, file_db_entry)
            self.add_attributes('hashes_populated', True)
            self.add_attributes('signatures_populated', True)
            return

        if len(missing_files) == 0:
        # sha1 and signature fields populated as expected
            self._update_file_list_sha1_and_signature_from_db(db_path)


    def _populate_file_hash_and_signature_fields_without_db(self):
        disk_accessor = self._disk_accessor
        fs_handles = disk_accessor.get_file_system_handles()
        if self._files and not self._attributes['hashes_populated']:
            print('Populating file signatures and hashes without file database.')
            before_hash = time.time()
            for each_file in self._files:
                try:
                    fs_handle = fs_handles[each_file.partition_sector]
                    each_file.populate_hash_and_signature_field(hash_size_limit=max_file_size_for_sha1_calculation, fs_handle=fs_handle)
                except Exception as e:
                    print(f"Hashing failed for: {each_file.full_path} with Exception {e}")
                    continue
            after_hash = time.time()
            print(print('Hashing took {} seconds'.format(after_hash - before_hash)))
            self.add_attributes('hashes_populated', True)
            self.add_attributes('signatures_populated', True)


    def _populate_file_hash_and_signature_fields_with_db(self, db_path):
        disk_accessor = self._disk_accessor
        fs_handles = disk_accessor.get_file_system_handles()
        if self._files and not self._attributes['hashes_populated']:
            for each_file in self._files:
                fs_handle = fs_handles[each_file.partition_sector]
                each_file.populate_hash_and_signature_field(hash_size_limit=max_file_size_for_sha1_calculation,
                                                            fs_handle=fs_handle)
                file_db_entry = each_file.to_dict()
                self._add_entry_to_db(db_path, file_db_entry)
            self.add_attributes('hashes_populated', True)
            self.add_attributes('signatures_populated', True)


    @staticmethod
    def _add_entry_to_db(db_path, file_db_entry):
        # need to flatten timestamps
        file_db_entry['a_time'] = file_db_entry['timestamps']['a_time']
        file_db_entry['cr_time'] = file_db_entry['timestamps']['cr_time']
        file_db_entry['m_time'] = file_db_entry['timestamps']['m_time']
        del file_db_entry['timestamps']

        # noinspection SqlResolve, SqlNoDataSourceInspection
        query = '''
            INSERT INTO files (evidence_name, file_size, full_path, inode, meta_path, partition_sector, sha1, signature, a_time, cr_time, m_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(query, (
            file_db_entry['evidence_name'],
            file_db_entry['file_size'],
            file_db_entry['full_path'],
            file_db_entry['inode'],
            file_db_entry['meta_path'],
            file_db_entry['partition_sector'],
            file_db_entry['sha1'],
            file_db_entry['signature'],
            file_db_entry['a_time'],
            file_db_entry['cr_time'],
            file_db_entry['m_time']
        ))

        conn.commit()

        conn.close()

    @staticmethod
    def _update_values_of_entry_in_db(db_path, file_db_entry):
        # need to flatten timestamps
        file_db_entry['a_time'] = file_db_entry['timestamps']['a_time']
        file_db_entry['cr_time'] = file_db_entry['timestamps']['cr_time']
        file_db_entry['m_time'] = file_db_entry['timestamps']['m_time']
        del file_db_entry['timestamps']

        # noinspection SqlResolve, SqlNoDataSourceInspection
        query = '''
                UPDATE files
                SET evidence_name = ?, file_size = ?, meta_path = ?, partition_sector = ?, sha1 = ?, signature = ?, 
                    a_time = ?, cr_time = ?, m_time = ?
                WHERE inode = ? OR full_path = ?
            '''

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(query, (
            file_db_entry['evidence_name'],
            file_db_entry['file_size'],
            file_db_entry['meta_path'],
            file_db_entry['partition_sector'],
            file_db_entry['sha1'],
            file_db_entry['signature'],
            file_db_entry['a_time'],
            file_db_entry['cr_time'],
            file_db_entry['m_time'],
            file_db_entry['inode'],     # identifier
            file_db_entry['full_path']  # identifier
        ))

        conn.commit()

        conn.close()

    def _remove_and_save_existing_db_file(self, db_path):
        new_db_path = f"{db_path}{int(time.time())}.save"
        shutil.move(db_path, new_db_path)  # Renames the existing file
        print(f"Existing database for {self.image_path} moved from {db_path} to {new_db_path}")

    def _create_and_update_db_file(self, db_path):
        print(f"Creating and populating new file list database with file signatures and hashes at {db_path}.")
        self._create_new_db_file(db_path)
        self._populate_file_hash_and_signature_fields_with_db(db_path)

    @staticmethod
    def _is_file_table_layout_as_expected(db_path) -> bool:
        # TODO: check existence of files table, check if columns are as expected
        return True

    def _files_not_in_db_file_list(self, db_path):
        # compare file list with db
        file_list = self._files
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # files that are not yet in the database
        missing_files = []

        for each_file in file_list:
            # check if file exists
            # noinspection SqlResolve, SqlNoDataSourceInspection
            query = """
                            SELECT EXISTS(SELECT 1 FROM files WHERE inode = ? AND full_path = ?)
                        """
            cursor.execute(query, (each_file.inode, each_file.full_path))
            result = cursor.fetchone()[0]

            # If file not found in db -> missing
            if not result:
                missing_files.append(each_file)

        # Close the connection
        conn.close()

        # Return the list of missing files
        return missing_files


    def _files_sha1_and_signature_not_populated_as_expected(self, db_path):
        # compare file list of disk image obj. with db
        # check if file signature is not None and sha1 ist not none for files <= max_file_size_for_sha1_calculation
        file_list = self._files
        hash_size_limit = max_file_size_for_sha1_calculation
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # files that are yet in the database but either signature is not populate or sha1 is not populated despite the file size being below limit
        unpopulated_files = []

        for each_file in file_list:
            # noinspection SqlResolve, SqlNoDataSourceInspection
            query = """
                                    SELECT sha1, signature FROM files WHERE inode = ? AND full_path = ?
                                """
            cursor.execute(query, (each_file.inode, each_file.full_path))
            result = cursor.fetchone()
            if result:
                sha1, signature = result
                if ((sha1 is None or sha1 == '') and each_file.file_size <= hash_size_limit) or signature is None:
                    unpopulated_files.append(each_file)

        conn.close()

        # Return the list of files where either sha1 or signature is not populated as expected
        return unpopulated_files


    @staticmethod
    def _create_new_db_file(db_path):

        open(db_path, 'wb')

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # noinspection SqlResolve, SqlNoDataSourceInspection
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_name TEXT,
                file_size INTEGER,
                full_path TEXT,
                inode INTEGER,
                meta_path TEXT,
                partition_sector INTEGER,
                sha1 TEXT,
                signature TEXT,
                a_time INTEGER,
                cr_time INTEGER,
                m_time INTEGER
            )
        ''')

        conn.commit()
        conn.close()

    def _update_file_list_sha1_and_signature_from_db(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f'Loading file signatures and hashes from existing file list database.')

        for each_file in self._files:

            # noinspection SqlResolve, SqlNoDataSourceInspection
            cursor.execute("""
                    SELECT sha1, signature FROM files WHERE inode = ? AND full_path = ?
                """, (each_file.inode,each_file.full_path))

            result = cursor.fetchone()

            if result:
                sha1, signature = result
                each_file.sha1 = sha1
                each_file.signature = bytes.fromhex(signature)

        # Close the database connection
        conn.close()
        self.add_attributes('hashes_populated', True)
        self.add_attributes('signatures_populated', True)