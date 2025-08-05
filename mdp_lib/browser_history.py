import os
import re
import sqlite3
from abc import abstractmethod
from typing import List, Dict

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class SearchEngine(object):
    def __init__(self, name, pattern):
        self.name = name
        # pattern should match the possible url structures for the respective search engine
        # only matching text searches right now not specific ones like images/news etc. on subdomains
        self.pattern = pattern

    def is_search_query(self, url):
        # this is probably not perfect and might lead to some false positives (e.g. #q=)
        is_search_query = re.search(self.pattern, url, re.IGNORECASE) and "q=" in url
        return is_search_query


class GoogleSearch(SearchEngine):
    def __init__(self):
        # source: https://www.google.com/supported_domains
        super().__init__('Google', r"https?://(www\.)?google\.[a-z]{2,3}(\.[a-z]{2})?")


class BingSearch(SearchEngine):
    def __init__(self):
        super().__init__('Bing', r"https?://(www\.)?bing\.com")


class DuckDuckGoSearch(SearchEngine):
    def __init__(self):
        super().__init__('DuckDuckGo', r"https?://(www\.)?duckduckgo\.com")


class BrowserHistory(MDPPlugin):
    name = ''
    description = ''
    include_in_data_table = False

    @abstractmethod
    def process_disk(self, target_disk_image: TargetDiskImage):
        # define pattern to locate the history file
        # define sql query to get rows of url+visit_count
        # define list of search engines to consider
        # create mdp result using analyze_history_file
        pass

    # example: analyze_history_file('chrome', target_disk_image, chrome_history_pattern, query, [GoogleSearch(), BingSearch(), DuckDuckGoSearch()])
    # query needs to give results with rows where row[0] is url and row [1] is visit_count
    def analyze_history_file(self, browser_name: str, target_disk_image: TargetDiskImage, history_pattern: str,
                             query: str, search_engines: List[SearchEngine]) -> dict[str, int | None]:
        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'

        history_count_max = None
        history_count_total = None
        no_history_files = None
        total_search_counts: Dict[str, int | None] = {engine.name: None for engine in search_engines}
        max_search_counts: Dict[str, int | None] = {engine.name: None for engine in search_engines}

        for each_file in files:
            if re.search(history_pattern, each_file.full_path, re.IGNORECASE):
                with open(temp_filename, 'wb') as f:
                    f.write(each_file.read())
                try:
                    conn = sqlite3.connect(temp_filename)
                    cursor = conn.cursor()
                    cursor.execute(query)
                    results = cursor.fetchall()

                    current_history_count = 0
                    current_search_counts = {engine.name: 0 for engine in search_engines}

                    # TODO: Not sure whether this will work for other browsers too -> maybe enforce that result of the query has this format, exception handling
                    for row in results:
                        url = row[0]
                        visit_count = row[1]

                        current_history_count += visit_count
                        for engine in search_engines:
                            if engine.is_search_query(url):
                                current_search_counts[engine.name] += visit_count

                    if history_count_max:
                        history_count_max = max(history_count_max, current_history_count)
                        history_count_total = history_count_total + current_history_count
                        no_history_files += 1
                    else:
                        history_count_max = current_history_count
                        history_count_total = current_history_count
                        no_history_files = 1

                    for engine in search_engines:
                        if max_search_counts[engine.name]:
                            max_search_counts[engine.name] = max(max_search_counts[engine.name],
                                                                 current_search_counts[engine.name])
                            total_search_counts[engine.name] += current_search_counts[engine.name]
                        else:
                            max_search_counts[engine.name] = current_search_counts[engine.name]
                            total_search_counts[engine.name] = current_search_counts[engine.name]

                    conn.close()

                except sqlite3.Error as e:
                    print(f"SQLite error: {e}")
                    break
                except Exception as e:
                    print(f"General error: {e}")
                    break
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

        results_dict = {
            browser_name + '_no_history_files': no_history_files,
            browser_name + '_history_entries_max': history_count_max,
            browser_name + '_history_entries_total': history_count_total
        }

        for engine in search_engines:
            results_dict[browser_name + f'_{engine.name.lower()}_searches_max'] = max_search_counts[engine.name]
            results_dict[browser_name + f'_{engine.name.lower()}_searches_total'] = total_search_counts[engine.name]

        return results_dict
