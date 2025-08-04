import os.path
import re
import subprocess

import config.config as config
import mdp_lib.plugin_result
from mdp_lib.disk_image_info import TargetDiskImage


class Plaso(object):

    name = 'plaso'
    description = 'Run plaso against disk'
    include_in_data_table = True

    # Note: this plugin increases processing time drastically for the first run,
    #   plugin result fields are generated dynamically based on event_types detected by plaso, no predetermined results-list
    def process_disk(self, target_disk_image: TargetDiskImage):

        evidence_path, image_name = os.path.split(target_disk_image.image_path)
        case_path = os.path.dirname(evidence_path)

        # add image file name as prefix to all output files
        plaso_folder = os.path.join(case_path, "plaso-output")
        prefix = os.path.join(plaso_folder, image_name)
        plaso_file_path = f"{prefix}.plaso"
        log2timeline_log = f"{prefix}.log2timeline.log.gz"
        psort_log = f"{prefix}.psort.log.gz"
        pinfo_log = f"{prefix}.pinfo.log.gz"

        path_to_plaso_csv = f"{prefix}.plaso.csv"
        pinfo_txt = f"{prefix}.pinfo.txt"


        # check if plaso-output folder exists
        plaso_folder_exists = os.path.exists(plaso_folder)
        if not plaso_folder_exists:
            os.makedirs(plaso_folder)

        # Check if files relevant for our metrics already exist
        csv_exists = os.path.exists(path_to_plaso_csv)
        pinfo_exists = os.path.exists(pinfo_txt)

        if csv_exists and pinfo_exists:
            print(f"Skipping Plaso run - using existing {path_to_plaso_csv} and {pinfo_txt}")
            with open(pinfo_txt, 'r') as f:
                pinfo_output = f.read()
        else:
            path_to_venv_python3 = config.path_to_venv_python3
            path_to_plaso_scripts = config.path_to_plaso_scripts

            # this method of calling programs is bad
            # but is a solution since we want the venv set up for plaso
            # https://stackoverflow.com/questions/8052926/running-subprocess-within-different-virtualenv-with-python

            devnull = open(os.devnull, 'w')

            # Run log2timeline
            cmd = [
                path_to_venv_python3,  # needs to point to plaso venvs python3 executable
                f"{path_to_plaso_scripts}/log2timeline.py",
                "--logfile", log2timeline_log,
                "--partitions", "all",
                "--vss_stores=none",
                "--storage-file", plaso_file_path,
                target_disk_image.image_path
            ]

            print("Plaso cmd:")
            print(print(' '.join(cmd)))
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            if os.path.exists(path_to_plaso_csv):
                os.remove(path_to_plaso_csv)

            # Convert to CSV
            cmd = [
                path_to_venv_python3,
                f"{path_to_plaso_scripts}/psort.py",
                "--logfile", psort_log,
                "-o", "dynamic",
                "-w", path_to_plaso_csv,
                plaso_file_path
            ]

            print("psort cmd:")
            print(' '.join(cmd))

            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # get info from .plaso to pinfo
            cmd = [
                path_to_venv_python3,
                f"{path_to_plaso_scripts}/pinfo.py",
                "--logfile", pinfo_log,
                plaso_file_path
            ]

            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)

            pinfo_output = output.decode()

            # Save pinfo output to text
            with open(pinfo_txt, 'w') as f:
                f.write(pinfo_output)


        # Extract all lines from pinfo that are like: "event_type_name : 123"
        # create list of event_types dynamically
        count_dict = {}
        for line in pinfo_output.splitlines():
            match = re.match(r'^\s*([a-z0-9_]+)\s*:\s*(\d+)', line)
            if match:
                event_type = match.group(1)
                count = int(match.group(2))
                count_dict[event_type] = count

        count = 0
        f = open(path_to_plaso_csv)
        for _ in f:
            count += 1

        res = mdp_lib.plugin_result.MDPResult(target_disk_image.image_path, self.name, self.description)
        res.results = {'plaso_events_csv_total': count}

        for each in count_dict:
            res.results['plaso_{}'.format(each)] = count_dict[each]

        return res


# just a way to test a plugin quickly
if __name__ == '__main__':
    a = Plaso()

    test_image_path = 'path to disk image'
    disk_image_object = mdp_lib.disk_image_info.TargetDiskImage(test_image_path)
    res = a.process_disk(disk_image_object)
    print(res)


# full list of plaso plugins (2024-03-27)
# from log2timeline.py --info
# *********************************** Parsers ************************************
#                  Name : Description
# --------------------------------------------------------------------------------
#     android_app_usage : Parser for Android usage history (usage-history.xml)
#                         files.
#               asl_log : Parser for Apple System Log (ASL) files.
#               bencode : Parser for Bencoded files.
#        binary_cookies : Parser for Safari Binary Cookie files.
#              bodyfile : Parser for SleuthKit version 3 bodyfile.
#               bsm_log : Parser for Basic Security Module (BSM) event auditing
#                         files.
#          chrome_cache : Parser for Google Chrome or Chromium Cache files.
#    chrome_preferences : Parser for Google Chrome Preferences files.
#              cups_ipp : Parser for CUPS IPP files.
#   custom_destinations : Parser for Custom destinations jump list
#                         (.customDestinations-ms) files.
#                  czip : Parser for Compound ZIP files.
#                 esedb : Parser for Extensible Storage Engine (ESE) Database
#                         File (EDB) format.
#              filestat : Parser for file system stat information.
#         firefox_cache : Parser for Mozilla Firefox Cache version 1 file
#                         (version 31 or earlier).
#        firefox_cache2 : Parser for Mozilla Firefox Cache version 2 file
#                         (version 32 or later).
#          fish_history : Parser for Fish history files.
#             fseventsd : Parser for MacOS File System Events Disk Log Stream
#                         (fseventsd) files.
#              java_idx : Parser for Java WebStart Cache IDX files.
#                 jsonl : Parser for JSON-L log files.
#                   lnk : Parser for Windows Shortcut (LNK) files.
#       locate_database : Parser for Locate database file (updatedb).
#          mac_keychain : Parser for MacOS keychain database files.
#     mcafee_protection : Parser for McAfee Anti-Virus access protection log
#                         files.
#                   mft : Parser for NTFS $MFT metadata files.
#                msiecf : Parser for Microsoft Internet Explorer (MSIE) 4 - 9
#                         cache (index.dat) files.
# networkminer_fileinfo : Parser for NetworkMiner .fileinfos files.
#                 olecf : Parser for OLE Compound File (OLECF) format.
#          onedrive_log : Parser for OneDrive Log files.
#          opera_global : Parser for Opera global history (global_history.dat)
#                         files.
#   opera_typed_history : Parser for Opera typed history (typed_history.xml)
#                         files.
#                    pe : Parser for Portable Executable (PE) files.
#                 plist : Parser for Property list (plist) files.
#            pls_recall : Parser for PL SQL cache file (PL-SQL developer recall
#                         file) format.
#              prefetch : Parser for Windows Prefetch File (PF).
#           recycle_bin : Parser for Windows $Recycle.Bin $I files.
#     recycle_bin_info2 : Parser for Windows Recycler INFO2 files.
#                 rplog : Parser for Windows Restore Point log (rp.log) files.
#            simatic_s7 : Parser for SIMATIC S7 Log files.
#     spotlight_storedb : Parser for Apple Spotlight store database (store.db)
#                         files.
#                sqlite : Parser for SQLite database files.
#      symantec_scanlog : Parser for Symantec AV Corporate Edition and Endpoint
#                         Protection log files.
#       systemd_journal : Parser for Systemd journal files.
#                  text : Parser for text-based log files.
#        trendmicro_url : Parser for Trend Micro Office Web Reputation log files.
#         trendmicro_vd : Parser for Trend Micro Office Scan Virus Detection log
#                         files.
#       unified_logging : Parser for Apple Unified Logging (AUL) 64-bit tracev3
#                         files.
#               usnjrnl : Parser for NTFS USN change journal ($UsnJrnl:$J) file
#                         system metadata files.
#                  utmp : Parser for Linux libc6 utmp files.
#                 utmpx : Parser for Mac OS X 10.5 utmpx files.
#             wincc_sys : Parser for WinCC Sys Log files.
#   windefender_history : Parser for Windows Defender scan DetectionHistory
#                         files.
#                winevt : Parser for Windows EventLog (EVT) files.
#               winevtx : Parser for Windows XML EventLog (EVTX) files.
#                winjob : Parser for Windows Scheduled Task job (or at-job)
#                         files.
#            winpca_db0 : Parser for Windows PCA DB0 log files.
#            winpca_dic : Parser for Windows PCA DIC log files.
#                winreg : Parser for Windows NT Registry (REGF) files.
# --------------------------------------------------------------------------------
#
# ******************************** Parser Plugins ********************************
#                                 Name : Description
# --------------------------------------------------------------------------------
#                              airport : Parser for Airport plist files.
#                              amcache : Parser for AMCache (AMCache.hve).
#                        android_calls : Parser for Android call history SQLite
#                                        database (contacts2.db) files.
#                       android_logcat : Parser for Android logcat files.
#                          android_sms : Parser for Android text messages (SMS)
#                                        SQLite database (mmssms.dbs) files.
#                      android_webview : Parser for Android WebView SQLite
#                                        database files.
#                 android_webviewcache : Parser for Android WebViewCache SQLite
#                                        database files.
#                        apache_access : Parser for Apache access log
#                                        (access.log) files.
#                       appcompatcache : Parser for Application Compatibility
#                                        Cache Registry data.
#                             apple_id : Parser for Apple account information
#                                        plist files.
#                             appusage : Parser for MacOS application usage
#                                        SQLite database
#                                        (application_usage.sqlite) files.
#                          apt_history : Parser for Advanced Packaging Tool
#                                        (APT) History log files.
#                   aws_cloudtrail_log : Parser for AWS CloudTrail Log.
#                       aws_elb_access : Parser for AWS ELB Access log files.
#                   azure_activity_log : Parser for Azure Activity Log.
# azure_application_gateway_access_log : Parser for Azure Application Gateway
#                                        access log.
#                               bagmru : Parser for BagMRU (or ShellBags)
#                                        Registry data.
#                                  bam : Parser for Background Activity
#                                        Moderator (BAM) Registry data.
#                         bash_history : Parser for Bash history files.
#                 bencode_transmission : Parser for Transmission BitTorrent
#                                        activity files.
#                     bencode_utorrent : Parser for uTorrent active torrent
#                                        files.
#                             ccleaner : Parser for CCleaner Registry data.
#                    chrome_17_cookies : Parser for Google Chrome 17 - 65
#                                        cookies SQLite database files.
#                    chrome_27_history : Parser for Google Chrome 27 and later
#                                        history SQLite database files.
#                    chrome_66_cookies : Parser for Google Chrome 66 and later
#                                        cookies SQLite database files.
#                     chrome_8_history : Parser for Google Chrome 8 - 25 history
#                                        SQLite database files.
#                      chrome_autofill : Parser for Google Chrome autofill
#                                        SQLite database (Web Data) files.
#            chrome_extension_activity : Parser for Google Chrome extension
#                                        activity SQLite database files.
#                    confluence_access : Parser for Confluence access log
#                                        (access.log) files.
#              docker_container_config : Parser for Docker container
#                                        configuration files.
#                 docker_container_log : Parser for Docker container log files.
#                  docker_layer_config : Parser for Docker layer configuration
#                                        files.
#                                 dpkg : Parser for Debian package manager log
#                                        (dpkg.log) files.
#                              dropbox : Parser for Dropbox sync history
#                                        database (sync_history.db) files.
#                 edge_load_statistics : Parser for SQLite database files.
#                explorer_mountpoints2 : Parser for Windows Explorer mount
#                                        points Registry data.
#               explorer_programscache : Parser for Windows Explorer Programs
#                                        Cache Registry data.
#                         file_history : Parser for Windows 8 File History ESE
#                                        database files.
#                   firefox_10_cookies : Parser for Mozilla Firefox cookies
#                                        SQLite database file version 10.
#                firefox_118_downloads : Parser for Mozilla Firefox 118
#                                        downloads SQLite database
#                                        (downloads.sqlite) files.
#                    firefox_2_cookies : Parser for Mozilla Firefox cookies
#                                        SQLite database file version 2.
#                    firefox_downloads : Parser for Mozilla Firefox downloads
#                                        SQLite database (downloads.sqlite)
#                                        files.
#                      firefox_history : Parser for Mozilla Firefox history
#                                        SQLite database (places.sqlite) files.
#                              gcp_log : Parser for Google Cloud (GCP) log.
#                       gdrive_synclog : Parser for Google Drive Sync log files.
#                         google_drive : Parser for Google Drive snapshot SQLite
#                                        database (snapshot.db) files.
#                            googlelog : Parser for Google-formatted log files.
#                    hangouts_messages : Parser for Google Hangouts
#                                        conversations SQLite database (babel.db)
#                                        files.
#                             imessage : Parser for MacOS and iOS iMessage
#                                        database (chat.db, sms.db) files.
#              ios_application_privacy : Parser for iOS Application Privacy
#                                        report.
#                          ios_carplay : Parser for Apple iOS Car Play
#                                        application plist files.
#                        ios_datausage : Parser for iOS data usage SQLite
#                                        databse (DataUsage.sqlite) file..
#                 ios_identityservices : Parser for Idstatuscache plist files.
#                        ios_lockdownd : Parser for iOS lockdown daemon log.
#                             ios_logd : Parser for iOS sysdiagnose logd files.
#                         ios_netusage : Parser for iOS network usage SQLite
#                                        database (netusage.sqlite) files.
#                         ios_powerlog : Parser for iOS powerlog SQLite database
#                                        (CurrentPowerlog.PLSQL) files.
#                       ios_screentime : Parser for iOS Screen Time SQLite
#                                        database (RMAdminStore-Local.sqlite).
#                      ios_sysdiag_log : Parser for iOS sysdiag log.
#                          ipod_device : Parser for iPod, iPad and iPhone plist
#                                        files.
#                              kik_ios : Parser for iOS Kik messenger SQLite
#                                        database (kik.sqlite) files.
#                                 kodi : Parser for Kodi videos SQLite database
#                                        (MyVideos.db) files.
#                        launchd_plist : Parser for Launchd plist files.
#                        ls_quarantine : Parser for MacOS launch services
#                                        quarantine events database SQLite
#                                        database files.
#                  mac_appfirewall_log : Parser for MacOS Application firewall
#                                        log (appfirewall.log) files.
#                mac_document_versions : Parser for MacOS document revisions
#                                        SQLite database files.
#                       mac_knowledgec : Parser for MacOS Duet/KnowledgeC
#                                        SQLites database files.
#                            mac_notes : Parser for MacOS Notes SQLite database
#                                        (NotesV7.storedata) files.
#               mac_notificationcenter : Parser for MacOS Notification Center
#                                        SQLite database files.
#                        mac_securityd : Parser for MacOS security daemon
#                                        (securityd) log files.
#                             mac_wifi : Parser for MacOS Wi-Fi log (wifi.log)
#                                        files.
#                      mackeeper_cache : Parser for MacOS MacKeeper cache SQLite
#                                        database files.
#         macos_background_items_plist : Parser for Mac OS backgrounditems.btm
#                                        or BackgroundItems-v[3-9].btm plist
#                                        files.
#                      macos_bluetooth : Parser for MacOS Bluetooth plist files.
#                macos_install_history : Parser for MacOS installation history
#                                        plist files.
#                    macos_launchd_log : Parser for Mac OS launchd log files.
#              macos_login_items_plist : Parser for Mac OS
#                                        com.apple.loginitems.plist files.
#             macos_login_window_plist : Parser for Mac OS login window plist
#                                        files.
#                macos_software_update : Parser for MacOS software update plist
#                                        files.
#             macos_startup_item_plist : Parser for Mac OS startup item plist
#                                        files.
#                             macostcc : Parser for MacOS Transparency, Consent,
#                                        Control (TCC) SQLite database (TCC.db)
#                                        files.
#                              macuser : Parser for MacOS user plist files.
#                  microsoft_audit_log : Parser for Microsoft (Office) 365 audit
#                                        log.
#                 microsoft_office_mru : Parser for Microsoft Office MRU
#                                        Registry data.
#                microsoft_outlook_mru : Parser for Microsoft Outlook search MRU
#                                        Registry data.
#              mrulist_shell_item_list : Parser for Most Recently Used (MRU)
#                                        Registry data.
#                       mrulist_string : Parser for Most Recently Used (MRU)
#                                        Registry data.
#            mrulistex_shell_item_list : Parser for Most Recently Used (MRU)
#                                        Registry data.
#                     mrulistex_string : Parser for Most Recently Used (MRU)
#                                        Registry data.
#      mrulistex_string_and_shell_item : Parser for Most Recently Used (MRU)
#                                        Registry data.
# mrulistex_string_and_shell_item_list : Parser for Most Recently Used (MRU)
#                                        Registry data.
#                        msie_webcache : Parser for Internet Explorer WebCache
#                                        ESE database (WebCacheV01.dat,
#                                        WebCacheV24.dat) files.
#                            msie_zone : Parser for Microsoft Internet Explorer
#                                        zone settings Registry data.
#                            mstsc_rdp : Parser for Terminal Server Client
#                                        Connection Registry data.
#                        mstsc_rdp_mru : Parser for Terminal Server Client Most
#                                        Recently Used (MRU) Registry data.
#                       network_drives : Parser for Windows network drives
#                                        Registry data.
#                             networks : Parser for Windows networks
#                                        (NetworkList) Registry data.
#         olecf_automatic_destinations : Parser for Automatic destinations jump
#                                        list OLE compound file
#                                        (.automaticDestinations-ms).
#                        olecf_default : Parser for Generic OLE compound item.
#               olecf_document_summary : Parser for Document summary information
#                                        (\0x05DocumentSummaryInformation).
#                        olecf_summary : Parser for Summary information
#                                        (\0x05SummaryInformation) (top-level
#                                        only).
#                                 oxml : Parser for OpenXML (OXML) files.
#                        plist_default : Parser for plist files.
#                   popularity_contest : Parser for Popularity Contest log files.
#                           postgresql : Parser for PostgreSQL application log
#                                        files.
#                powershell_transcript : Parser for PowerShell transcript event.
#                     safari_downloads : Parser for Safari Downloads plist files.
#                       safari_history : Parser for Safari history plist files.
#                     safari_historydb : Parser for Safari history SQLite
#                                        database (History.db) files.
#                                santa : Parser for Santa log (santa.log) files.
#                                 sccm : Parser for System Center Configuration
#                                        Manager (SCCM) client log files.
#                              selinux : Parser for SELinux audit log
#                                        (audit.log) files.
#                             setupapi : Parser for Windows SetupAPI log files.
#                      skydrive_log_v1 : Parser for OneDrive (or SkyDrive)
#                                        version 1 log files.
#                      skydrive_log_v2 : Parser for OneDrive (or SkyDrive)
#                                        version 2 log files.
#                                skype : Parser for Skype SQLite database
#                                        (main.db) files.
#                        snort_fastlog : Parser for Snort3/Suricata fast-log
#                                        alert log (fast.log) files.
#                            sophos_av : Parser for Sophos anti-virus log file
#                                        (SAV.txt) files.
#                            spotlight : Parser for Spotlight searched terms
#                                        plist files.
#                     spotlight_volume : Parser for Spotlight volume
#                                        configuration plist files.
#                                 srum : Parser for System Resource Usage
#                                        Monitor (SRUM) ESE database files.
#                               syslog : Parser for System log (syslog) files.
#                   syslog_traditional : Parser for Traditional system log
#                                        (syslog) files.
#                tango_android_profile : Parser for Tango on Android profile
#                                        SQLite database files.
#                     tango_android_tc : Parser for Tango on Android TC SQLite
#                                        database files.
#                         time_machine : Parser for MacOS TimeMachine plist
#                                        files.
#                      twitter_android : Parser for Twitter on Android SQLite
#                                        database files.
#                          twitter_ios : Parser for Twitter on iOS 8 and later
#                                        SQLite database (twitter.db) files.
#                  user_access_logging : Parser for Windows User Access Logging
#                                        ESE database files.
#                           userassist : Parser for User Assist Registry data.
#                              viminfo : Parser for Viminfo files.
#                               vsftpd : Parser for vsftpd log files.
#                 windows_boot_execute : Parser for Boot Execution Registry data.
#                  windows_boot_verify : Parser for Windows boot verification
#                                        Registry data.
#              windows_eventtranscript : Parser for Windows diagnosis
#                                        EventTranscript SQLite database
#                                        (EventTranscript.db) files.
#                          windows_run : Parser for Run and run once Registry
#                                        data.
#                    windows_sam_users : Parser for Security Accounts Manager
#                                        (SAM) users Registry data.
#                     windows_services : Parser for Windows drivers and services
#                                        Registry data.
#                     windows_shutdown : Parser for Windows last shutdown
#                                        Registry data.
#                   windows_task_cache : Parser for Windows Task Scheduler cache
#                                        Registry data.
#                     windows_timeline : Parser for Windows 10 timeline SQLite
#                                        database (ActivitiesCache.db) files.
#                     windows_timezone : Parser for Windows time zone Registry
#                                        data.
#                   windows_typed_urls : Parser for Windows Explorer typed URLs
#                                        Registry data.
#                  windows_usb_devices : Parser for Windows USB device Registry
#                                        data.
#              windows_usbstor_devices : Parser for Windows USB Plug And Play
#                                        Manager USBStor Registry data.
#                      windows_version : Parser for Windows version (product)
#                                        Registry data.
#                          winfirewall : Parser for Windows Firewall log files.
#                               winiis : Parser for Microsoft IIS log files.
#                             winlogon : Parser for Windows log-on Registry data.
#                           winrar_mru : Parser for WinRAR History Registry data.
#                       winreg_default : Parser for Windows Registry data.
#                             xchatlog : Parser for XChat log files.
#                      xchatscrollback : Parser for XChat scrollback log files.
#                            zeitgeist : Parser for Zeitgeist activity SQLite
#                                        database files.
#                 zsh_extended_history : Parser for ZSH extended history files.