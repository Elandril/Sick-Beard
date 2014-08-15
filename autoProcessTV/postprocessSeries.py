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
import subprocess
import shutil
from send2trash import send2trash

# Hachoir
from hachoir_core import config
config.use_i18n = False  # Don't use i18n
config.quiet = True      # Don't display warnings
from hachoir_parser import createParser
from hachoir_core.compatibility import all
from hachoir_core.i18n import getTerminalCharset

# settings
reallyDelete = True
mkvtoolnix_path = r"C:\Program Files\Multimedia\MKVToolNix"
handbrake_path  = r"C:\Program Files\Multimedia\Handbrake"

# 0  sys.argv[0] is the name of this script

# 1  The final full path to the episode file
if len(sys.argv) < 2:
    print ("No file supplied - is this being called from Sick Beard?")
    sys.exit(1)
else:
    dl_file_fullpath = sys.argv[1]
    dl_path, dl_file = os.path.split(dl_file_fullpath)
    dl_path = os.path.normpath(dl_path)
    dl_file_basename, dl_file_ext = os.path.splitext(dl_file)
    dl_file_ext = dl_file_ext.lower()

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
    mkv.stream._input.close()
    if hasCueV3:
        print(' - found CueRelativePosition or CueDuration elements')
        tmp_file = os.path.join(dl_path, dl_file_basename + '_temp.mkv')
        mkv_cmd = [ os.path.join(mkvtoolnix_path, 'mkvmerge.exe'),
                    '-o', tmp_file,
                    '--engage', 'no_cue_duration',
                    '--engage', 'no_cue_relative_position',
                    dl_file_fullpath ]
        print(u" - Executing command " + unicode(str(mkv_cmd),charset))
        p = subprocess.Popen(mkv_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd='.')
        out, err = p.communicate()  # @UnusedVariable
        print(u" - Script result (return code {:d}):\n".format(p.returncode) + unicode(str(out), charset))
        if p.returncode == 0:
            # everything went OK
            if not reallyDelete:
                shutil.move(dl_file_fullpath, os.path.join(dl_path, dl_file_basename + '_orig.mkv'))
            else:
                send2trash(dl_file_fullpath)
            shutil.move(tmp_file, dl_file_fullpath)
        elif p.returncode == 1:
            # Warnings
            new_orig_file = os.path.join(dl_path, dl_file_basename + '_orig.mkv')
            print(' - there were warnings; original file retained as "{}"'.format(new_orig_file))
            shutil.move(dl_file_fullpath, new_orig_file)
            shutil.move(tmp_file, dl_file_fullpath)
        else:
            # Errors
            print(' - there were errors; file remains unchanged! Please check temporary output file {}'.format(tmp_file))

    else:
        print(' - all OK => nothing to do')
elif dl_file_ext == ".ts":
    # convert .ts files into .mkv files
    isInterleaved = re.search('\W(1080|720)i\W', org_filename, re.I) is not None
    print(' - interleaved: {}'.format(isInterleaved))
else:
    print(' => nothing to do')
