#!/usr/bin/env python

# Sick Beard allows additional post processing scripts to be called after its own processing. It passes 5 parameters to these scripts:

# 1. final full path to the episode file
# 2. original name of the episode file
# 3. show tvdb id
# 4. season number
# 5. episode number
# 6. episode air date

import os.path
import sys
from locale import setlocale, LC_ALL
import re

# Hachoir
from hachoir_core import config
config.use_i18n = False  # Don't use i18n
config.quiet = True      # Don't display warnings
from hachoir_parser import createParser
from hachoir_core.compatibility import all
from hachoir_core.i18n import getTerminalCharset

# settings
reallyDelete = False

# 0  sys.argv[0] is the name of this script

# 1  The final full path to the episode file
if len(sys.argv) < 2:
    print ("No file supplied - is this being called from Sick Beard?")
    sys.exit(1)
else:
    dl_file_fullpath = sys.argv[1]
    dl_path, dl_file = os.path.split(dl_file_fullpath)
    _, dl_file_ext = os.path.splitext(dl_file.lower())

# 2  The original name of the episode file
org_filename = sys.argv[2] if len(sys.argv) > 3 else None

# 3  show tvdb id
tvdb_id = sys.argv[3] if len(sys.argv) > 4 else None

# 4  season number
ep_season = sys.argv[4] if len(sys.argv) > 5 else None

# 5  episode number
ep_number = sys.argv[5] if len(sys.argv) > 6 else None

# 6  episode air date
ep_airdate = sys.argv[6] if len(sys.argv) > 7 else None


def mkvFindCueV3(parser):
    for s in parser:
        if s.name.startswith("Segment["):
            for cue in s["Cues"]:
                if cue.name.startswith("CuePoint["):
                    for cp in cue:
                        if cp.name.startswith("CueTrackPositions["):
                            for ctp in cp:
                                if ctp.name.startswith("CueRelativePosition") or ctp.name.startswith("CueDuration"):
                                    #print('{}: {}'.format(ctp.path,ctp.name))
                                    return True
    return False

# settings for Hachoir (unicode)
setlocale(LC_ALL, "C")
charset = getTerminalCharset()

print('Examining {}:\n - file type is {}'.format(dl_file_fullpath, dl_file_ext))

if dl_file_ext == ".mkv":
    # check if CueDuration or CueRelativePosition are present
    # and remove them if neccessary
    mkv = createParser(unicode(dl_file_fullpath,charset))
    hasCueV3 = mkvFindCueV3(mkv)
    if hasCueV3:
        print(' - found CueRelativePosition or CueDuration elements')
    else:
        print(' - all OK => nothing to do')
elif dl_file_ext == ".ts":
    # convert .ts files into .mkv files
    isInterleaved = re.search('\W(1080|720)i\W', org_filename, re.I) is not None
    print(' - interleaved: {}'.format(isInterleaved))
