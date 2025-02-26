import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.browser_history import BrowserHistory, GoogleSearch, BingSearch, DuckDuckGoSearch, SearchEngine


class EdgeHistory(BrowserHistory):
    name = 'edge_history'
    description = 'Information about the Edge history for Edge v79+, Windows 7+'
    include_in_data_table = True

    def process_disk(self, target_disk_image: TargetDiskImage):
        pattern_edge_windows = r'/Users/[^/]+/AppData/Local/Microsoft/Edge/User Data/[^/]+/History$'

        edge_history_pattern = r'P_[0-9]+(' + pattern_edge_windows + r')'

        # noinspection SqlResolve, SqlNoDataSourceInspection
        query = """
            SELECT 
                urls.url,
                urls.visit_count
            FROM 
                urls
            """

        search_engines = [GoogleSearch(), BingSearch(), DuckDuckGoSearch()]

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)

        res.results = super().analyze_history_file('edge', target_disk_image, edge_history_pattern, query,
                                                   search_engines)

        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = EdgeHistory()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)