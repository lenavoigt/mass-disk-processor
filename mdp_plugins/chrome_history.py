import mdp_lib.mdp_plugin
from mdp_lib.browser_history import BrowserHistory, GoogleSearch, BingSearch, DuckDuckGoSearch
from mdp_lib.disk_image_info import TargetDiskImage


class ChromeHistory(BrowserHistory):
    name = 'chrome_history'
    description = 'Information about the Google Chrome history from History (including chromium on Linux)'
    # NOTE: This doesnt work for MacOS atm
    expected_results = [
        'chrome_no_history_files',
        'chrome_history_entries_max',
        'chrome_history_entries_total',
        'chrome_google_searches_max',
        'chrome_google_searches_total',
        'chrome_bing_searches_max',
        'chrome_bing_searches_total',
        'chrome_duckduckgo_searches_max',
        'chrome_duckduckgo_searches_total',
    ]

    def process_disk(self, target_disk_image: TargetDiskImage):
        pattern_windows = r'/(Users|Documents and Settings|Dokumente und Einstellungen)/[^/]+/(AppData/Local|Local Settings/Application Data|Lokale Einstellungen/Anwendungsdaten)/Google/Chrome/User Data/[^/]+'
            # C:\Users\<username>\AppData\Local\Google\Chrome\User Data\<Profile>\History
            # C:\Documents and Settings\<username>\Local Settings\Application Data\Google\Chrome\User Data\<Profile>\History
            # C:\Dokumente und Einstellungen\<username>\Lokale Einstellungen\Anwendungsdaten\Google\Chrome\User Data\<Profile>\History

        pattern_linux = r'/home/[^/]+/(snap/chromium/common/|\.config/)(chromium|google-chrome)/[^/]+'
            # /home/<username>/snap/chromium/common/chromium/<Profile>/History
            # /home/<username>/.config/chromium/<Profile>/History
            # /home/<username>/.config/google-chrome/<Profile>/History

        # pattern_macos = r''

        chrome_history_pattern = r'P_[0-9]+((' + pattern_windows + r')|(' + pattern_linux + r'))/History$'

        # noinspection SqlResolve, SqlNoDataSourceInspection
        query = """
                SELECT urls.url,
                       urls.visit_count
                FROM urls \
                """
        search_engines = [GoogleSearch(), BingSearch(), DuckDuckGoSearch()]

        result_dict = super().analyze_history_file('chrome', target_disk_image, chrome_history_pattern, query,
                                                   search_engines)
        result = self.create_result(target_disk_image)
        self.set_results(result, result_dict)

        return result