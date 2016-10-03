# pervade
Automatic e-book formatter for Wildbow's online serial, Worm.

Basic usage:  
Download entire series: `python3 pervade.py`


Output of `python3 pervade.py -h`:  
```
usage: pervade.py [-h] [-a [ARC# [ARC# ...]]] [-c [CHAP# [CHAP# ...]]] [-d]
                  [-j] [-s SECONDS] [-v] [-x]

optional arguments:
  -h, --help            show this help message and exit
  -a [ARC# [ARC# ...]], --arc [ARC# [ARC# ...]]
                        select arc(s) to download (by index, not by title)
  -c [CHAP# [CHAP# ...]], --chapter [CHAP# [CHAP# ...]]
                        select chapter(s) to download (by index, not by title)
  -d, --download        explicitly set to download mode
  -j, --join            join all files of the same arc
  -s SECONDS, --seconds SECONDS
                        time to wait after page load in seconds (automatically
                        fuzzed)
  -v, --verbose         display more verbose output for debugging
  -x, --debug           display only errors and debugging messages
```
