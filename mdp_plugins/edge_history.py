from mdp_lib.browser_history import BrowserHistory, GoogleSearch, BingSearch, DuckDuckGoSearch
from mdp_lib.disk_image_info import TargetDiskImage


class EdgeHistory(BrowserHistory):
    name = 'edge_history'
    description = 'Information about the Edge history for Edge v79+, Windows 7+'
    include_in_data_table = True
    expected_results = [
        'edge_no_history_files',
        'edge_history_entries_max',
        'edge_history_entries_total',
        'edge_google_searches_max',
        'edge_google_searches_total',
        'edge_bing_searches_max',
        'edge_bing_searches_total',
        'edge_duckduckgo_searches_max',
        'edge_duckduckgo_searches_total',
    ]

    def process_disk(self, target_disk_image: TargetDiskImage):
        pattern_edge_windows = r'/Users/[^/]+/AppData/Local/Microsoft/Edge/User Data/[^/]+/History$'

        edge_history_pattern = r'P_[0-9]+(' + pattern_edge_windows + r')'

        # noinspection SqlResolve, SqlNoDataSourceInspection
        query = """
                SELECT urls.url,
                       urls.visit_count
                FROM urls \
                """

        search_engines = [GoogleSearch(), BingSearch(), DuckDuckGoSearch()]

        result_dict = super().analyze_history_file('edge', target_disk_image, edge_history_pattern, query,
                                                   search_engines)

        result = self.create_result(target_disk_image)
        self.set_results(result, result_dict)

        return result