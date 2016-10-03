#Pervade
Automatic e-book formatter for Wildbow's online serial, Worm. Currently, output format targets AbiWord and as such may not appear correctly in other viewing applications.

###Basic usage:

Print index of series: `python3 pervade.py`  
Download entire series: `python3 pervade.py -d`  
Download individual arc `x`: `python3 pervade.py -a x -j`  
Download set of arbitrary arcs `x`, `y`, `z`: `python3 pervade.py -a x y z -j`  
Download individual chapter `a` of arc `x`: `python3 pervade.py -a x -c a`  
Download set of arbitrary chapters `a`, `b`, `c` of arc `x`: `python3 pervade.py -a x -c a b c`

***

###Help:

Files can be converted faithfully to PDF with the command: `abiword --to=pdf *.rtf`

***

###TODO:

1. Identify all usages of <span> tag so that a catch-all can be added for all incidences that have no effect on formatting.

***

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

***

*Justice Shall Pervade*
