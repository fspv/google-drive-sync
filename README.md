Synchronize local files to corresponding Google Drive locations.

The app is currently best effort and fails loudly in case things went wrong.

The synchronization works both ways and is based on file timestamps. Whichever file has the largest modified time wins and get synchronized. Having that in mind - beware of data races and race conditions. Not suitable for data that might be edited from multiple places simultaneously.

Installation
============

Install google api client
```
pip install google-api-python-client
```

Auth is a tricky part here. The best I managed to come up so far is:
```
gcloud auth revoke
gcloud auth login --enable-gdrive-access
export GOOGLE_APPLICATION_CREDENTIALS=${HOME}/.config/gcloud/legacy_credentials/<email>/adc.json
```
Let me know if there is an easier way.

Running
=======

Usage:
```
$ python3 google-drive-sync.py --help
usage: google-drive-sync.py [-h] -s SYNC [SYNC ...] [-i INTERVAL]

Synchronise specified files the with corresponding Google Drive documents

options:
  -h, --help            show this help message and exit
  -s SYNC [SYNC ...], --sync SYNC [SYNC ...]
                        Local file path and Google Drive file id separated by comma
  -i INTERVAL, --interval INTERVAL
                        How often to check for changes (in seconds)
```

Example:
```
./google-drive-sync.py -s test.txt,1xX-XXXXXXXX_YYYYYYYY -s test2.txt,AAAAAAAAAA_BBBBBBBBBB -i 30
```

TODO
====

[ ] Make async to support syncing many files in parallel
[ ] Introduce inotify + subscribe to Google Drive notifications to avoid busy-waiting for changes
