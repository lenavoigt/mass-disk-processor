from mdp_lib.browser_history import BrowserHistory, GoogleSearch, BingSearch, DuckDuckGoSearch
from mdp_lib.disk_image_info import TargetDiskImage


class FirefoxHistory(BrowserHistory):
    name = 'firefox_history'
    description = 'Information about the Mozilla Firefox history in moz_places of places.sqlite'
    # NOTE: This doesnt work for MacOS atm
    expected_results = [
        'firefox_no_history_files',
        'firefox_history_entries_max',
        'firefox_history_entries_total',
        'firefox_google_searches_max',
        'firefox_google_searches_total',
        'firefox_bing_searches_max',
        'firefox_bing_searches_total',
        'firefox_duckduckgo_searches_max',
        'firefox_duckduckgo_searches_total',
    ]

    def process_disk(self, target_disk_image: TargetDiskImage):
        pattern_windows = r'/(Users|Documents and Settings|Dokumente und Einstellungen)/[^/]+/(AppData/Roaming|Application Data|Anwendungsdaten)/Mozilla/Firefox/Profiles/[^/]+\.default[^/]*'
                # C:\Users\<username>\AppData\Roaming\Mozilla\Firefox\Profiles\xxxxxxxx.default\places.sqlite
                # C:\Documents and Settings\<username>\Application Data\Mozilla\Firefox\Profiles\xxxxxxxx.default\places.sqlite
                # C:\Dokumente und Einstellungen\<username>\Anwendungsdaten\Mozilla\Firefox\Profiles\xxxxxxxx.default\places.sqlite
        pattern_linux = r'/home/[^/]+/(snap/firefox/common/)?\.mozilla/firefox/[^/]+\.default[^/]*'
                # /home/<username>/snap/firefox/common/.mozilla/firefox/xxxxxxxx.default/places.sqlite
                # /home/<username>/.mozilla/firefox/xxxxxxxx.default-release/places.sqlite
        # pattern_macos = r''

        firefox_places_pattern = r'P_[0-9]+((' + pattern_windows + r')|(' + pattern_linux + r'))/places\.sqlite$'

        # noinspection SqlResolve, SqlNoDataSourceInspection
        query = """
                SELECT moz_places.url,
                       moz_places.visit_count
                FROM moz_places \
                """

        search_engines = [GoogleSearch(), BingSearch(), DuckDuckGoSearch()]

        result_dict = super().analyze_history_file('firefox', target_disk_image, firefox_places_pattern, query,
                                                   search_engines)
        result = self.create_result(target_disk_image)
        self.set_results(result, result_dict)

        return result

        # Maybe at some point we'll also want to do sth with the visit date and other stuff?
        # query = """
        #                         SELECT
        #                             moz_places.id,
        #                             moz_places.url,
        #                             moz_places.title,
        #                             moz_places.visit_count,
        #                             moz_historyvisits.visit_date
        #                         FROM
        #                             moz_places
        #                         JOIN
        #                             moz_historyvisits
        #                         ON
        #                             moz_places.id = moz_historyvisits.place_id
        #                         ORDER BY
        #                             moz_places.id ASC;
        #                         """
