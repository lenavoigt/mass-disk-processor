import os
import re
from typing import List

from marple.file_object import FileItem

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class FileTypes(MDPPlugin):
    name = 'file_types'
    description = 'Number of different file types. (And number of file signature mismatches if file signature fields are populated.)'
    expected_results = [
        'pdf_files',
        'office_files',
        'image_files',
        'audio_files',
        'video_files',
        'compressed_files',
        'no_signature_mismatches'
    ]

    # NOTE: This is just a first suggestion of which categories of file types to create and what to include
    # This dict should probably be stored somewhere else

    # Categorizations from:
    # https://www.garykessler.net/library/file_sigs.html
    # https://sceweb.sce.uhcl.edu/abeysekera/itec3831/labs/FILE%20SIGNATURES%20TABLE.pdf
    # https://en.wikipedia.org/wiki/List_of_file_signatures
    file_categories = {
        'pdf_files': {
            '.pdf': [{'signature': '25504446', 'offset': 0}],
        },
        'office_files': {
            '.doc': [{'signature': 'D0CF11E0A1B11AE1', 'offset': 0}],
            '.docx': [{'signature': '504B030414000600', 'offset': 0}],
            '.xls': [{'signature': 'D0CF11E0A1B11AE1', 'offset': 0}],
            '.xlsx': [{'signature': '504B030414000600', 'offset': 0}],
            '.ppt': [{'signature': 'D0CF11E0A1B11AE1', 'offset': 0}],
            '.pptx': [{'signature': '504B030414000600', 'offset': 0}],
            '.odt': [{'signature': '504B0304', 'offset': 0}],
            '.ods': [{'signature': '504B0304', 'offset': 0}],
            '.odp': [{'signature': '504B0304', 'offset': 0}],
        },
        'image_files': {
            '.jpg': [{'signature': 'FFD8', 'offset': 0}],
            '.jpeg': [{'signature': 'FFD8', 'offset': 0}],
            '.bmp': [{'signature': '424D', 'offset': 0}],
            '.png': [{'signature': '89504E470D0A1A0A', 'offset': 0}],
            '.gif': [{'signature': '474946383761', 'offset': 0},
                     {'signature': '474946383961', 'offset': 0}],
            '.heic': [{'signature': '6674797068656963', 'offset': 4}],
        },
        'audio_files': {
            '.mp3': [{'signature': '494433', 'offset': 0},
                     {'signature': 'FFF', 'offset': 0}],
            '.wav': [{'signature': '52494646', 'offset': 0}],
            '.flac': [{'signature': '664C6143', 'offset': 0}],
            '.wma': [{'signature': '3026B2758E66CF11A6D900AA0062CE6C', 'offset': 0}],
            '.m4a': [{'signature': '667479704D344120', 'offset': 4}],
        },
        'video_files': {
            '.mp4': [{'signature': '66747970', 'offset': 4}],
            '.avi': [{'signature': '52494646', 'offset': 0}],
            '.mkv': [{'signature': '1A45DFA3', 'offset': 0}],
            '.webm': [{'signature': '1A45DFA3', 'offset': 0}],
            '.mov': [{'signature': '66747970', 'offset': 4}],
            '.wmv': [{'signature': '3026B2758E66CF11A6D900AA0062CE6C', 'offset': 0}],
            '.flv': [{'signature': '464C56', 'offset': 0}],
            # '.mpeg': [{'signature': '47', 'offset': 0}, # Info I found on this didnt match in different sources, skipping for now
            #           {'signature': '000001B', 'offset': 0}],
            # '.mpg': [{'signature': '47', 'offset': 0},
            #           {'signature': '000001B', 'offset': 0}],
        },
        'compressed_files': {
            '.zip': [{'signature': '504B0304', 'offset': 0}],
            '.rar': [{'signature': '526172211A07', 'offset': 0}],
            '.7z': [{'signature': '377ABCAF271C', 'offset': 0}],
            '.tar': [{'signature': '7573746172', 'offset': 257}],
            '.gz': [{'signature': '1F8B08', 'offset': 0}],
        }
    }
        # 'encrypted_files' : {
        #     '.tc',
        #     '.hc'
        # }

    @staticmethod
    def is_mismatch_file_signature_with_offset(encountered_signature: str, expected_signature: str, byte_offset: int) -> bool:
        expected_len = len(expected_signature)
        encountered_len = len(encountered_signature)

        offset = byte_offset*2
        # We cannot compare here due to limited amount of data available in the file signature field of encountered file
        # -> NOTE: doesnt count as a mismatch
        if offset >= encountered_len:
            return False

        # How many bytes are left for comparison? -> we only return a mismatch, but no certainty on whether its a match
        chars_to_compare = min(encountered_len - offset, expected_len)

        # Only mismatches where we are certain return true
        if encountered_signature[offset:offset + chars_to_compare].lower() != expected_signature[:chars_to_compare].lower():
            return True

        return False

    def is_mismatch_file_signature_and_extension(self, encountered_signature: str, file_extension: str) -> bool:

        file_extension = file_extension.lower()

        for category, extensions in self.file_categories.items():
            if file_extension in extensions:
                expected_signatures = extensions[file_extension]

                for signature_details in expected_signatures:
                    expected_signature = signature_details['signature']
                    offset = signature_details['offset']

                    # Only return true for mismatch when we are certain
                    if not self.is_mismatch_file_signature_with_offset(encountered_signature, expected_signature, offset):
                        # If any of the expected signatures match or it is uncertain whether they match, not a certain mismatch
                        return False

                # None of the expected signatures were (a match or at least uncertain) -> certain mismatch
                return True

        # uncertainty -> not a certain mismatch
        return False

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files: List[FileItem] = disk_image.files

        no_signature_mismatches = None

        file_category_count = {category: 0 for category in self.file_categories}

        category_patterns = {}

        for category, extensions in self.file_categories.items():
            pattern = r'.*(' + '|'.join([re.escape(ext) for ext in extensions]) + r')$'
            category_patterns[category] = pattern

        signatures_populated = target_disk_image.attributes['signatures_populated']

        if signatures_populated:
            no_signature_mismatches = 0
        else:
            print('File signature fields not populated. Skipping signature check.')

        for each in files:
            for category, pattern in category_patterns.items():
                _, file_ext = os.path.splitext(each.full_path)
                if re.match(pattern, each.full_path, re.IGNORECASE):
                    file_category_count[category] += 1
                    if signatures_populated and each.signature:
                        encountered_signature = ''
                        try:
                            encountered_signature = each.signature.hex()
                        except Exception as e:
                            print(e)
                            continue

                        if self.is_mismatch_file_signature_and_extension(encountered_signature,file_ext):
                            no_signature_mismatches += 1
                            # print('File: ', each.full_path, '\nSignature: ', each.signature, '; File Ext: ', file_ext)
                    break

        result = self.create_result(target_disk_image)

        for category, count in file_category_count.items():
            self.set_result(result, category, count)
            # print(f"{category}: {count}")

        self.set_result(result, 'no_signature_mismatches', no_signature_mismatches)

        return result
