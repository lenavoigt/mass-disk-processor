# from distutils.command.install import value

import mdp_lib.plugin_result
from mdp_lib.browser_history import BrowserHistory, GoogleSearch, BingSearch, DuckDuckGoSearch
from mdp_lib.disk_image_info import TargetDiskImage


class ChromeHistory(BrowserHistory):
    name = 'chrome_history'
    description = 'Information about the Google Chrome history from History (including chromium on Linux)'
    # NOTE: This doesnt work for MacOS atm
    include_in_data_table = True

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
                    SELECT
                        urls.url,
                        urls.visit_count
                    FROM
                        urls
                    """
        search_engines = [GoogleSearch(), BingSearch(), DuckDuckGoSearch()]

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)

        res.results = super().analyze_history_file('chrome', target_disk_image, chrome_history_pattern, query,
                                                   search_engines)

        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = ChromeHistory()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)

