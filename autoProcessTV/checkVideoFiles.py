#!/usr/bin/env python

from __future__ import print_function
import os.path
import sys
from locale import setlocale, LC_ALL
import re
import subprocess
import shutil
from send2trash import send2trash
import argparse
import glob
from pymediainfo import MediaInfo
import re

# Hachoir
from hachoir_core import config
config.use_i18n = False  # Don't use i18n
config.quiet = True      # Don't display warnings
from hachoir_parser import createParser
from hachoir_core.compatibility import all
from hachoir_core.i18n import getTerminalCharset
from hachoir_core.field import MissingField

# settings
mkvtoolnix_path = r"C:\Program Files\Multimedia\MKVToolNix"
handbrake_path  = r"C:\Program Files\Multimedia\Handbrake"
mediainfo_path = r"C:\Program Files\Multimedia\MediaInfo\cli"

os.environ['PATH'] = mediainfo_path + os.pathsep + os.environ['PATH']

actionList = {
    '.mkv': 'CLEAN_CUE_ELEMENTS',
    '.ts':  'CONVERT'
}

languages = {
    'de': 'German',
    'en': 'English'
}


def mkvFindCueV3(parser):
    try:
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
    except MissingField as e:
        print("Error: file '{0}' has no field '{1}' in '2'".format(parser.stream.source, e.key, e.field.path))
        return True
    return False

def checkAudioLanguages(file_fullpath, languages):
    mi = MediaInfo.parse(file_fullpath)
    audio = [t for t in mi.tracks if t.track_type=='Audio']
    audio.sort(key=lambda t: -t.track_id if t.default==u'Yes' else t.track_id)
    return True


def processFile(file_fullpath, dryrun=False, quiet=True, deleteMethod='trash', tempDir = None):
    file_path, file_name = os.path.split(file_fullpath)
    file_path = os.path.normpath(file_path)
    file_basename, file_ext = os.path.splitext(file_name)
    file_ext = file_ext.lower()
    if not tempDir:
        tempDir = file_path
    action = None
    success = False

    if not quiet: print('Examining {}:\n - file type is {}'.format(file_fullpath, file_ext))

    if file_ext == ".mkv":
        # check if CueDuration or CueRelativePosition are present
        # and remove them if neccessary
        mkv = createParser(unicode(file_fullpath,charset))
        hasCueV3 = mkvFindCueV3(mkv)
        mkv.stream._input.close()
        if hasCueV3:
            action = actionList['.mkv']
            if not quiet: print(' - found CueRelativePosition or CueDuration elements')
            if not dryrun:
                tmp_file = os.path.join(tempDir, file_basename + '_temp.mkv')
                mkv_cmd = [ os.path.join(mkvtoolnix_path, 'mkvmerge.exe'),
                            '-o', tmp_file,
                            '--engage', 'no_cue_duration',
                            '--engage', 'no_cue_relative_position',
                            file_fullpath ]
                if not quiet: print(u" - Executing command " + unicode(str(mkv_cmd),charset))
                p = subprocess.Popen(mkv_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd='.')
                out, err = p.communicate()  # @UnusedVariable
                if not quiet: print(u" - Script result (return code {:d}):\n".format(p.returncode) + unicode(str(out), charset))
                if p.returncode == 0:
                    # everything went OK
                    if deleteMethod == 'unlink':
                        os.unlink(file_fullpath)
                    elif deleteMethod == 'move':
                        shutil.move(file_fullpath, os.path.join(file_path, file_basename + '_orig.mkv'))
                    else:  # send to 'trash'
                        send2trash(file_fullpath)
                    shutil.move(tmp_file, file_fullpath)
                    success = True
                elif p.returncode == 1:
                    # Warnings
                    new_orig_file = os.path.join(file_path, file_basename + '_orig.mkv')
                    if not quiet: print(' - there were warnings; original file retained as "{}"'.format(new_orig_file))
                    shutil.move(file_fullpath, new_orig_file)
                    shutil.move(tmp_file, file_fullpath)
                    success = True
                else:
                    # Errors
                    if not quiet: print(' - there were errors; file remains unchanged! Please check temporary output file {}'.format(tmp_file))
                    success = False
        else:
            if not quiet: print(' - all OK => nothing to do')
            success = True

    elif file_ext == ".ts":
        # convert .ts files into .mkv files
        action = actionList['.ts']
        isInterleaved = re.search('\W(1080|720)i\W', org_filename, re.I) is not None
        if not quiet: print(' - interleaved: {}'.format(isInterleaved))
        if not dryrun:
            success = True

    else:
        if not quiet: print(' => nothing to do')
        success = True

    return (action, success)

def printAction(name, action, success, dryrun=False, printName=True):
    if printName:
        fmtstr = '{0}: {1}'
    else:
        fmtstr = ' {1}'
    if not dryrun:
        fmtstr += ' ({2})'
    if action:
        if success:
            print(fmtstr.format(name, action,"OK"))
        else:
            print(fmtstr.format(name, action,"FAILED"))
    elif not printName:
        print("")

# settings for Hachoir (unicode)
setlocale(LC_ALL, "C")
charset = getTerminalCharset()

parser = argparse.ArgumentParser()
parser.add_argument("file", help="video file to process", nargs="+")
parser.add_argument("-r", "--recursive", help="recursively search video files", action="store_true")
parser.add_argument("-d", "--dryrun", help="do not perform any actions", action="store_true")
parser.add_argument("-p", "--progress", help="print progress report", action="store_true")
parser.add_argument("-l", "--languages", help="test audio languages", type=lambda s: re.split(r'[\s,]+', s.lower()))
parser.add_argument("-t", "--temp", help="temporary working directory")
delGrp = parser.add_mutually_exclusive_group()
delGrp.add_argument("--erase", help="erase method", choices=['trash','move','unlink'], default='trash')
delGrp.add_argument("--trash", help="erase by sending to trash", action="store_const", dest='erase', const='trash')
delGrp.add_argument("--move", help="erase by moving to '_orig' file", action="store_const", dest='erase', const='move')
delGrp.add_argument("--unlink", help="erase by unlinking", action="store_const", dest='erase', const='unlink')
args = parser.parse_args()

#print(args.languages)
#print(args.temp)
#exit(0)

#if args.trash:
#    deleteMethod = 'trash'
#elif args.move:
#    deleteMethod = 'move'
#elif args.unlink:
#    deleteMethod = 'unlink'
#else:
#    deleteMethod = args.erase
deleteMethod = args.erase
if args.dryrun:
    print("running in dryrun mode")
else:
    print("erase method: {}".format(deleteMethod))

if args.temp:
    temp_dir = os.path.abspath(args.temp)
else:
    temp_dir = None

#print(args.temp)
#print(temp_dir)
#exit(0)

filelist = []
for fn in args.file:
    filelist += glob.glob(os.path.expandvars(fn))

for fn in filelist:
    if args.recursive and os.path.isdir(fn):
        for root, dirs, files in os.walk(fn, followlinks=True):
            for name in files:
                name_full = os.path.join(root, name)
                if args.progress: print(name_full + " ...", end="")
                action, success = processFile(name_full, dryrun=args.dryrun, deleteMethod=args.erase, tempDir=temp_dir)
                printAction(name_full, action, success, dryrun=args.dryrun, printName=(not args.progress))
    elif os.path.isfile(fn):
        if args.progress: print(fn + " ...", end="")
        action, success = processFile(fn, dryrun=args.dryrun, deleteMethod=args.erase, tempDir=temp_dir)
        printAction(fn, action, success, dryrun=args.dryrun, printName=(not args.progress))
    else:
        print("Error: '{}' is not a valid file".format(fn))