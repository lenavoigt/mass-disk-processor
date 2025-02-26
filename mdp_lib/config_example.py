# copy this file to config.py and update details for plaso to work
# install plaso dependencies as per instructions

path_to_venv_python = '/set/path/to/installed/plaso/venv/activate'
path_to_plaso_scripts = '/set/path/to/plaso/scripts/folder'

# Specify path to a minimal RDSv3 (downloaded from: https://www.nist.gov/itl/ssd/software-quality-group/national-software-reference-library-nsrl/nsrl-download/current-rds)
# current implementation: this db has to have a table "FILE" with a column "sha1"
path_to_nsrl = None
# path_to_nsrl = '/set/path/to/nsrl/db'

# Preprocessing

# Set True if preprocessing should include population of file signature field in file list of a disk image
# High increase of preprocessing time
populate_file_signatures = False
# Set True if preprocessing should include sha1 hash value calculation and population of file signature field in file list of a disk image
# Even higher increase of preprocessing time
populate_file_hashes_and_signatures = False
# Specify maximum size of files where sha1 should be computed during pre-processing
max_file_size_for_sha1_calculation = 1000 # 1 KB

# Set True if db should be used to store file lists (with sha1 and signatures) and load file info from file list if available
use_db_for_file_lists = False