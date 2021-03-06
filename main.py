#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import datetime
import hashlib
from math import floor
import io
import os
import piexif
import pickle
import json
from PIL import Image, UnidentifiedImageError
import imagehash
import numpy
import pathlib
import photohash
import pprint
import re
import requests
import time
import traceback
import sys
import subprocess
from shutil import copy2

ROOT_DIR = os.path.abspath(os.getcwd())
IMPORTER_DIR = os.path.abspath(os.path.dirname(__file__))
DEST_DIR = os.path.abspath(os.path.dirname(__file__))
ARGS = None
pp = pprint.PrettyPrinter()
pprint = pp.pprint

IMPORT_DIR = None

EXTENSIONS_TO_IMPORT = [
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "tiff",
    "raw",
    "mov",
    "mp4",
    "avi",
    "aac",
    "dng",
    "wav",
    "mp3",
    "aiff",
    "pdf",
    "psd",
    "GIS",
]
PARTIALS_TO_IGNORE = [
    "tmp",
    "idx",
    ".thumbnails",
    "fseventsd-uuid",
    "shadowIndex",
    "StoreFile",
    "live.0",
    ".Spotlight",
    ".DS_Store",
    ".plist",
    # "~",
    "Generated Images.bundle",  # Mylio
    "Anki",  # Mylio
    "1Password",  # Mylio
    ".MYLock",  # Mylio
    ".graffle",
    ".Sparkle",
    ".app/",
]
IMAGE_EXTENSIONS = [
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "tiff",
    "raw",
    "crw",
    "dng",
]
EXTENSIONS_TO_IGNORE = [
    "xmp",
    "xml",
    "plist",
]

# Strings that might already be in the filename from previous systems, and what device to map them to.
DEVICE_SUBSTRINGS = {
    "haetori_DJI": "haetori",
    "pocket_DJI": "pocket",
    "pocket_GIS": "pocket",
    "sony": "sonya10",
    "pixel_edna": "pixel3_edna",
    "pixel": "pixel2",
    "300d": "digitalrebel",
    "htcevo": "htcevo",
    "-F1C11A22": "switch",
}

DEVICE_REGEXES = {
    # 2018070223400200-F1C11A22FAEE3B82F21B330E1B786A39.mp4
    "switch": "^[1-2][90]\d{12}00-[A-F0-9]{32}\.",

}
DATE_PARSERS = {
    "switch": "^[1-2][90]\d{12}",
    "import_script": "^[1-2][90]\d\d-\d\d\-\d\d_\d\d-\d\d-\d\d_",
    "older_camera": "^[1-2][90]\d\d-\d\d\-\d\d \d\d\.\d\d\.\d\d",
    "older_video": "^[1-2][90]\d\d-\d\d\-\d\d \d\d\.\d\d",
    "pixel_video": "^VID_[1-2][90]\d\d\d\d\d\d_\d\d\d\d\d\d\.",
    # Screen shot 2010-09-13 at 2.35.39 PM
    "mac_screenshot_upper": "^Screen Shot [1-2][90]\d\d-\d\d-\d\d at \d+\.\d+\.\d+. [AP]M",
    "mac_screenshot_lower": "^Screen shot [1-2][90]\d\d-\d\d-\d\d at \d+\.\d+\.\d+. [AP]M",
}
DATE_FORMAT_PATTERNS = {
    # 2018070223400200-F1C11A22FAEE3B82F21B330E1B786A39.mp4
    "switch": "%Y%m%d%H%M%S",
    "import_script": "%Y-%m-%d_%H-%M-%S_",
    "older_camera": "%Y-%m-%d %H.%M.%S",
    "older_video": "%Y-%m-%d %H.%M",
    "pixel_video": "VID_%Y%m%d_%H%M%S.",
    "mac_screenshot_upper": "Screen Shot %Y-%m-%d at %I.%M.%S %p",
    "mac_screenshot_lower": "Screen shot %Y-%m-%d at %I.%M.%S %p",
}
# Maps from the EXIF Camera Name to the device name you want to use.
CAMERA_MODEL_MAPPINGS = {
    "Pixel 2": "pixel2",
    "Pixel 3": "pixel3_edna",
    "Osmo Pocket": "pocket",
    "OSMO MOBILE": "osmomobile",
    "Canon EOS DIGITAL REBEL": "digitalrebel",
    "EVO": "htcevo",
    "iPhone 5s": "iphone5se",
    "iPhone 5": "iphone5",
    "XT1049": "motox",
    "NIKON D600": "bonnienikon",
    "HTC One X": "htconex_edna",
    "Canon EOS REBEL T2i": "eosrebel_edna",
    "Canon EOS REBEL T3": "eosrebelt3_edna",
    "iPhone 6": "iphone6_edna",
    "iPhone 7": "iphone7_edna",
    "iPhone 6s": "iphone6s_edna",
    "iPhone 6s Plus": "iphone6splus_edna",
    "iPhone 6 Plus": "iphone6plus_edna",
    "GT-I9505": "gti9505_edna",
    "iPhone 4S": "iphone4s",
    "iPad mini 2": "ipadmini2_edna",
    "iPad Air": "ipadair",
    "iPhone8,4": "iphonese",
    "iPhone SE": "iphonese",
    "SM-G900I": "smg900i_edna",
    "FC7203": "haetori",
    "HERO3+Silver Edition": "goprohero3silver",
    "C905": "sonyericssonC905",
    "iPhone6,1": "iphone5s",
    "QCAM-AA": "htcevo",
    "iPod touch": "ipodtouch",
    "HTC One V": "htconev",
    "One V": "htconev",
    "SM-G900T": "samsunggalaxys5",
    "Canon PowerShot A630": "canona630",
    "PC36100": "htcevo4g",
    "iPad 2": "ipad2",
    "The Pinhole": "thepinhole",
    "Xolaroid 2000": "htcevo4g",
    "CYBERSHOT": "sonycybershot",
    "The Little Orange Box": "htcevo4g",
    "The Baerbl": "htcevo4g",
    "The FudgeCan": "htcevo4g",
    "NIKON D7000": "nikond7000",
    "K850i": "k850i",
    "C765UZ": "c765uz",
    "MG7500 series": "mg7500",
    "iPhone 5S": "iphone5s",
    "NIKON D200": "bonnie_nikond200",
    "Canon EOS 5D": "canoneos5d",
    "DSC-H20": "dsch20",
    "Canon EOS 6D": "canoneos6d",
    "E-M5": "olympusem5",
    "LiDE 100": "canonlide100",
    "Galaxy Nexus": "galaxynexus",
}
EXTRA_CAMERA_MAPPINGS = {}
# Maps device names to a prettier display format.
DEVICE_DISPLAYNAME_MAPPINGS = {
    "sonya10": "Sony PCM-A10",
    "pixel2": "Google Pixel 2",
    "pixel3_edna": "Google Pixel 3 (Edna's)",
    "pocket": "DJI Osmo Pocket",
    "haetori": "DJI Mavic Mini",
    "digitalrebel": "Canon EOS Digital Rebel",
    "htcevo": "HTC Evo",
    "unknown": "Unknown Device",
    "iphone5se": "iPhone 5 SE",
    "iphone5": "iPhone 5 Edna",
    "motox": "Moto X",
    "osmomobile": "DJI Osmo Mobile",
    "bonnienikon": "Bonnie's Nikon D600",
    "switch": "Nintendo Switch",
    "htconex_edna": "HTC One X",
    "eosrebel_edna": "EOS Rebel T2i Edna",
    "eosrebelt3_edna": "EOS Rebel T3 Edna",
    "iphone6_edna": "iPhone 6",
    "iphone6s_edna": "iPhone 6s",
    "iphone7_edna": "iPhone 7",
    "iphone6splus_edna": "iPhone 6s Plus",
    "iphone6plus_edna": "iPhone 6 Plus",
    "gti9505_edna": "GT-I9505",
    "iphone4s": "iPhone 4S",
    "ipadmini2_edna": "iPad mini 2",
    "smg900i_edna": "SM-G900I",
    "iphonese": "iPhone SE",
    "iphonese_japan": "iPhone SE Japan",
    "goprohero3silver": "HERO3+Silver Edition",
    "sonyericssonC905": "Sony Ericsson C905",
    "ipadair": "iPad Air",
    "iphone5s": "iPhone6,1",
    "ipodtouch": "iPod Touch",
    "htconev": "HTC One V",
    "samsunggalaxys5": "Samsung Galaxy S5",
    "canona630": "Canon PowerShot A630",
    "htcevo4g": "HTC Evo 4G",
    "ipad2": "iPad 2",
    "thepinhole": "The Pinhole",
    "xolaroid2000": "Xolaroid 2000",
    "sonycybershot": "Sony Cybershot",
    "nikond7000": "Nikon D7000",
    "k850i": "Sony Ericsson Cybershot K650i",
    "c765uz": "Olympus C-765",
    "mg7500": "Canon PIXMA MG7500",
    "iphone5s": "iPhone 5S",
    "bonnie_nikond200": "Nikon D200",
    "canoneos5d": "Canon EOS 5D",
    "dsch20": "Sony Cybershot DSC-H20",
    "canoneos6d": "Canon EOS 6D",
    "olympusem5": "Olympus OM-D E-M5",
    "canonlide100": "Canon LiDE 100",
    "galaxynexus": "Galaxy Nexus",

}
LOCATIONIQ_TOKEN = "e49f9326982f23"
LOCATIONIQ_TOKEN = "1110c037a46791"

COUNTRY_MAPPINGS = {
    "United States of America": "USA"
}
CITY_MAPPINGS = {
    "Autonomous City of Buenos Aires": "Buenos Aires",
    "Kyoto-shi": "Kyoto",
    "Corona de Tucson": "Tucson",
    "Queenstown-Lakes": "Queenstown",
    "Maha Phruettharam": "Bangkok",
    "Maha Phruettharam District": "Bangkok",
    "Maha Phruettharam Subdistrict": "Bangkok",
    "Si Lom Subdistrict": "Bangkok",
    "Cache County": "Logan",
    "Cache": "Logan",
}
CITY_REPLACEMENTS = {
    " District": "",
    " Province": "",
    " County": "",
    " Region": "",
    " Subdistrict": "",
    "Departamento ": "",
    "Arrondissement of ": "",
}
COUNTRY_REPLACEMENTS = {
}
USA_NAMES = [
    "United States of America",
    "USA",
    "US"
]
PEOPLE = [
    "edna",
    "steven"
]
PRE_EXIF_GPS_LOCATIONS = {
    "steven-1980-04-09": {
        "country": "USA",
        "city": "Denver",
        "state": "Colorado",
    },
    "steven-1986-01-01": {
        "country": "USA",
        "city": "Gilbert",
        "state": "Arizona",
    },
    "steven-1998-08-01": {
        "country": "USA",
        "city": "Tucson",
        "state": "Arizona",
    },
    "steven-1999-06-01": {
        "country": "USA",
        "city": "San Diego",
        "state": "California",
    },
    "steven-2000-01-01": {
        "country": "USA",
        "city": "Escondido",
        "state": "California",
    },
    "steven-2003-01-01": {
        "country": "USA",
        "city": "San Diego",
        "state": "California",
    },
    "steven-2004-12-31": {
        "country": "USA",
        "city": "Ithaca",
        "state": "New York",
    },
    "steven-2005-12-02": {
        "country": "USA",
        "city": "Washington DC",
        "state": "Washington DC",
    },
    "steven-2005-12-04": {
        "country": "USA",
        "city": "Ithaca",
        "state": "New York",
    },
    "steven-2005-12-14": {
        "country": "USA",
        "city": "Baltimore",
        "state": "Maryland",
    },
    "steven-2005-12-25": {
        "country": "USA",
        "city": "Gilbert",
        "state": "Arizona",
    },
    "steven-2006-01-05": {
        "country": "USA",
        "city": "Ithaca",
        "state": "New York",
    },
    "steven-2007-05-26": {
        "country": "USA",
        "city": "Rehoboth Beach",
        "state": "Maryland",
    },
    "steven-2007-06-03": {
        "country": "USA",
        "city": "Ithaca",
        "state": "New York",
    },
    "steven-2008-06-01": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2010-05-21": {
        "country": "France",
        "city": "Paris",
        "state": "Ile-de-France",
    },
    "steven-2010-06-01": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2010-11-22": {
        "country": "USA",
        "city": "Palm Springs",
        "state": "California",
    },
    "steven-2010-11-27": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2011-02-11": {
        "country": "USA",
        "city": "Seattle",
        "state": "Washington",
    },
    "steven-2011-02-14": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2011-05-26": {
        "country": "USA",
        "city": "Fair Haven",
        "state": "New Jersey",
    },
    "steven-2011-06-01": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2011-08-12": {
        "country": "USA",
        "city": "Long Peak",
        "state": "Colorado",
    },
    "steven-2011-08-17": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2011-12-24": {
        "country": "USA",
        "city": "Phoenix",
        "state": "Arizona",
    },
    "steven-2011-12-27": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2012-04-01": {
        "country": "USA",
        "city": "Imnaha",
        "state": "Oregon",
    },
    "steven-2012-04-08": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2012-04-13": {
        "country": "USA",
        "city": "Las Vegas",
        "state": "Nevada",
    },
    "steven-2012-04-16": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2012-06-04": {
        "country": "USA",
        "city": "Minneapolis",
        "state": "Minnesota",
    },
    "steven-2012-06-10": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2012-06-27": {
        "country": "USA",
        "city": "San Francisco",
        "state": "California",
    },
    "steven-2012-07-02": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2012-07-26": {
        "country": "USA",
        "city": "Phoenix",
        "state": "Arizona",
    },
    "steven-2012-07-30": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2013-04-04": {
        "country": "USA",
        "city": "Orlando",
        "state": "Florida",
    },
    "steven-2013-04-07": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2013-09-28": {
        "country": "USA",
        "city": "Seattle",
        "state": "Washington",
    },
    "steven-2013-09-30": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2013-11-27": {
        "country": "USA",
        "city": "Logan",
        "state": "Utah",
    },
    "steven-2013-12-01": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2013-12-23": {
        "country": "USA",
        "city": "Tucson",
        "state": "Arizona",
    },
    "steven-2013-12-26": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2014-01-13": {
        "country": "Spain",
        "city": "Barcelona",
        "state": "Catalonia",
    },
    "steven-2014-01-25": {
        "country": "France",
        "city": "Paris",
        "state": "Ile-de-France",
    },
    "steven-2014-02-06": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2014-02-24": {
        "country": "USA",
        "city": "Las Vegas",
        "state": "Nevada",
    },
    "steven-2014-02-26": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2014-04-13": {
        "country": "USA",
        "city": "Imnaha",
        "state": "Oregon",
    },
    "steven-2014-04-20": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2014-05-03": {
        "country": "USA",
        "city": "Los Angeles",
        "state": "California",
    },
    "steven-2014-05-06": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2014-08-30": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2014-09-26": {
        "country": "USA",
        "city": "Seattle",
        "state": "Washington",
    },
    "steven-2014-09-29": {
        "country": "USA",
        "city": "Portland",
        "state": "Oregon",
    },
    "steven-2014-11-03": {
        "country": "USA",
        "city": "Gilbert",
        "state": "Arizona",
    },
    "steven-2014-11-06": {
        "country": "USA",
        "city": "Tucson",
        "state": "Arizona",
    },
    "steven-2014-11-11": {
        "country": "USA",
        "city": "Seattle",
        "state": "Washington",
    },
    "steven-2014-11-13": {
        "country": "Thailand",
        "city": "Phuket",
        "state": "Phuket",
    },
    "steven-2015-01-01": {
        "country": "Thailand",
        "city": "Phuket Town",
        "state": "Phuket",
    },
}
UNKNOWN_PLACE_NAME = "Unknown"
MAXIMUM_THUMBNAIL_HASH_DISTANCE = 8
MAXIMUM_IDENTICAL_HASH_DISTANCE = 1

if os.path.exists("/System/Applications/Preview.app"):
    preview_path = "/System/Applications/Preview.app"
elif os.path.exists("/Applications/Preview.app"):
    preview_path = "/Applications/Preview.app"
else:
    preview_path = ""


class Device(object):

    def __init__(self, name, regex_str, start_date, end_date=None):
        self.name = name
        self.regex_str = regex_str
        self.start_date = start_date

# Cybershot = Device("Cybershot", r"DSC*", datetime.date(2013, 12, 31))
# Cybershot = Device("Cybershot", "", datetime.date(2013, 12, 31))

try:
    with open('importamator.db', 'rb') as f:
        brain = pickle.load(f)
    print("✔ Loaded brain from importamator.db.")
    # print(brain)
except Exception as e:
    print("✔ No Brain Found, creating a new one.")
    brain = {}
    pass

if "date_country" not in brain:
    brain["date_country"] = {}
if "date_city" not in brain:
    brain["date_city"] = {}
if "date_state" not in brain:
    brain["date_state"] = {}
if "month_country" not in brain:
    brain["month_country"] = {}
if "imagehashes" not in brain:
    brain["imagehashes"] = {}

action_log = ""
now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
# now_str = "dev"

CACHED_FILE_INFO = {}

#  Backup to Server
# rsync -hPav /Volumes/MAPLE\ SEED/Capture "skoczen@hematite:/Volumes/Banded\ Iron/Movies/"

#
# 2019
#     - 01
#         2019-01-05_15-03-25_DJI_20191021_192436_1_video.mp4

try:

    def log_action(action):
        global action_log
        action_log += "\n%s" % action

    def convert_to_degrees(value):
        """Helper function to convert the GPS coordinates stored in the EXIF to degress in float format"""
        # From https://gist.github.com/erans/983821/e30bd051e1b1ae3cb07650f24184aa15c0037ce8
        d0 = value[0][0]
        d1 = value[0][1]
        d = float(d0) / float(d1)

        m0 = value[1][0]
        m1 = value[1][1]
        m = float(m0) / float(m1)

        s0 = value[2][0]
        s1 = value[2][1]
        s = float(s0) / float(s1)

        return d + (m / 60.0) + (s / 3600.0)

    def md5_file(file_path):
        buffer_size = 1048576  # 1MB chunks

        md5 = hashlib.md5()

        with open(file_path, 'rb') as f:
            while True:
                data = f.read(buffer_size)
                if not data:
                    break
                md5.update(data)

        return md5.hexdigest()

    def image_hashes(file_path):
        # image = Image.open(file_path)
        # img_size = 32
        # image = image.convert("L").resize((img_size, img_size), Image.ANTIALIAS)
        # pixels = numpy.asarray(image)

        # image.save("/Users/skoczen/Desktop/%s" % file_path.replace(ARGS.source_dir, "").replace(".jpg", "-thumb.jpg") , "JPEG")
        # log_action(file_path)
        # log_action(pixels)

        im = Image.open(file_path)
        hashes = [
            str(imagehash.phash(im, hash_size=16)),
            str(imagehash.phash(im.rotate(90), hash_size=16)),
            str(imagehash.phash(im.rotate(180), hash_size=16)),
            # TODO Technically, we only need three to ensure a match, but leaving this for now.
            # str(imagehash.phash(im.rotate(270), hash_size=16)),
        ]
        # print(hashes)
        return hashes
        # return photohash.average_hash(file_path)

    def sizeof_fmt(num, suffix='B'):
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.0f%s%s" % (num, 'Yi', suffix)

    def walk_tree(args):
        if not args.walk_dir:
            walk_dir = "."
        walk_dir = os.path.abspath(walk_dir)

        for dirpath, dirnames, filenames in os.walk(walk_dir, topdown=False):
            for filename in filenames:
                print(filename)
                sys.stdout.write(".")
                sys.stdout.flush()
                # if filename.endswith(".html") or filename.endswith(".xml"):
                import_file(filename)

    def prepare_import_dir(args):
        global IMPORT_DIR

        sys.stdout.write("\nPreparing %s..." % args.destination)
        sys.stdout.flush()

        importer_dir = os.path.join(args.destination,)
        IMPORT_DIR = importer_dir
        pathlib.Path(importer_dir).mkdir(parents=True, exist_ok=True)
        sys.stdout.write("done.")
        sys.stdout.flush()

    def import_file(source, dest, overwrite=False, dry_run=False):
        if dry_run:
            log_action("DRY RUN: Copying \n  %s to \n  %s" % (source, dest))
            return

        try:
            copy2(source, dest)
            log_action("Copied %s to %s\n" % (source, dest))
        except PermissionError:
            if os.path.getsize(source) == os.path.getsize(dest):
                pass
            else:
                raise PermissionError

    def write_temp_brain():
        with open('importamator.db.bak', "w+b") as f:
            pickle.dump(brain, f)

    def get_local_file_list(source_dir):
        files = []
        parse_dirs = []
        if os.path.islink(source_dir):
            source_dir = os.readlink(source_dir)
        else:
            parse_dirs.append(source_dir)

        for dirpath, dirnames, filenames in os.walk(source_dir, topdown=False):
            for dirname in dirnames:
                if os.path.islink(os.path.join(dirpath, dirname)):
                    if ".." in dirname:
                        parse_dirs.append(os.path.abspath(os.path.join(dirpath, os.readlink(os.path.join(dirpath, dirname)))))
                    else:
                        parse_dirs.append(os.path.abspath(os.path.join(os.path.join(dirpath, dirname))))
            for filename in filenames:
                if os.path.islink(os.path.join(dirpath, filename)):
                    parse_dirs.append(os.readlink(os.path.join(dirpath, filename)))

        for parse_dir in parse_dirs:
            for dirpath, dirnames, filenames in os.walk(parse_dir, topdown=False):
                if os.path.islink(dirpath):
                    pass
                else:
                    for filename in filenames:
                        if os.path.islink(os.path.join(dirpath, filename)):
                            if os.path.exists(os.readlink(os.path.join(dirpath, filename))):
                                files.append(os.readlink(os.path.join(dirpath, filename)))
                            else:
                                log_action("Could not find file symlinked from %s" % os.path.join(dirpath, filename))
                        else:
                            files.append(os.path.join(dirpath, filename))
                        sys.stdout.write(".")
                        sys.stdout.flush()
                # if filename.endswith(".html") or filename.endswith(".xml"):

        return files

    def ignored(file_path):
        if file_path.split(".")[-1].lower() in EXTENSIONS_TO_IGNORE:
            return True

        if not ARGS.all_files and file_path.split(".")[-1].lower() not in EXTENSIONS_TO_IMPORT:
            return True

        for p in PARTIALS_TO_IGNORE:
            if p in file_path:
                return True

        return False

    def eta(start_time, size_copied, total_size):
        if size_copied > 0:
            elapsed = datetime.datetime.now() - start_time
            rate = size_copied / elapsed.total_seconds()
            remaining_time = (total_size - size_copied) / rate
            remaining_hours = floor(remaining_time / 3600)
            remaining_minutes = floor((remaining_time - remaining_hours * 3600) / 60)
            remaining_seconds = floor((remaining_time - (remaining_hours * 3600) - (remaining_minutes * 60)))
            return "%02d:%02d:%02d" % (remaining_hours, remaining_minutes, remaining_seconds)
        return "Unknown"

    def get_file_metadata(file_path, exif_gps_only=False):
        global ARGS
        meta = {}
        error_str = None

        # Get file type from extension (which we trust, because why not. I'm not sniffing headers for this.)
        extension = file_path.split(".")[-1]
        meta["file_path"] = file_path
        meta["relative_file_path"] = file_path.replace(ARGS.source_dir, "").replace(ARGS.full_source_path, "")
        meta["extension"] = extension
        meta["source_name"] = file_path.split("/")[-1]
        meta["file_name"] = file_path.split("/")[-1]
        meta["is_image"] = extension.lower() in IMAGE_EXTENSIONS

        if exif_gps_only:
            log_action("Checked %s." % meta["relative_file_path"])

        if exif_gps_only and not meta["is_image"]:
            return meta

        # Capture Time.
        meta["datetime"] = None
        # Try to get from exif first.
        if meta["is_image"]:
            try:
                exif = piexif.load(file_path)
                meta["Camera Model"] = exif["0th"][272].decode().replace("\x00", "")
                meta["datetime"] = datetime.datetime.strptime(exif["0th"][306].decode(), "%Y:%m:%d %H:%M:%S")
                meta["exiftime"] = datetime.datetime.strptime(exif["0th"][306].decode(), "%Y:%m:%d %H:%M:%S")

                try:
                    meta["width"] = int(exif["0th"][256])
                    meta["height"] = int(exif["0th"][257])
                except:
                    pass

                meta["altitude"] = exif["GPS"][2]
                gps_ns = exif["GPS"][1].decode().upper()
                gps_latitude = exif["GPS"][2]
                gps_ew = exif["GPS"][3].decode().upper()
                gps_longitude = exif["GPS"][4]

                gps_sea_level = exif["GPS"][5]
                gps_altitude = exif["GPS"][6]

                # print(gps_altitude)
                # print(gps_sea_level)
                meta["sea_level"] = gps_sea_level
                meta["altitude"] = gps_altitude
                lat = None
                lon = None

                if gps_latitude and gps_ns and gps_longitude and gps_ew:
                    lat = convert_to_degrees(gps_latitude)
                    if gps_ns != "N":
                        lat = 0 - lat

                    lon = convert_to_degrees(gps_longitude)
                    if gps_ew != "E":
                        lon = 0 - lon

                if lat:
                    meta["lat"] = lat
                if lon:
                    meta["lon"] = lon
            except:
                # Use exiftool - `brew install exiftool`
                # Or https://exiftool.org/
                log_action("Falling back to exiftool for %s" % file_path)
                try:
                    result = subprocess.run(['exiftool', file_path], stdout=subprocess.PIPE)
                    exif_dict = {}
                    for line in result.stdout.decode().split("\n"):
                        try:
                            k, v = line.split(": ")
                            exif_dict[k.strip()] = v.strip()
                        except:
                            log_action("Skipping %s" % line)

                    meta["Camera Model"] = exif_dict["Camera Model Name"]
                    meta["width"] = int(exif_dict['Image Width'])
                    meta["height"] = int(exif_dict['Image Height'])
                    meta["datetime"] = datetime.datetime.strptime(exif_dict["Date/Time Original"].split(".")[0], "%Y:%m:%d %H:%M:%S")
                    meta["exiftime"] = datetime.datetime.strptime(exif_dict["Date/Time Original"].split(".")[0], "%Y:%m:%d %H:%M:%S")
                except Exception as e:
                    # pprint(exif_dict)
                    device_found = False
                    for device, r in DEVICE_REGEXES.items():
                        matches = re.findall(r, meta["file_name"])
                        if matches:
                            meta["device"] = device
                            device_found = True
                        break

                    for substring, device in DEVICE_SUBSTRINGS.items():
                        if substring in file_path.split("/")[-1]:
                            meta["device"] = device
                            device_found = True
                            break

                    if device_found:
                        # We're just using the local time because we don't know. Try to parse it from the filename.
                        if device in DATE_FORMAT_PATTERNS and device in DATE_PARSERS:
                            try:
                                matches = re.findall(DATE_PARSERS[device], meta["file_name"])
                                if matches:
                                    parsed_time = datetime.datetime.strptime(matches[0], DATE_FORMAT_PATTERNS[device])
                                    meta["datetime"] = parsed_time
                                    log_action("Replaced datetime with known time parsing for %s: %s" % (device, meta["datetime"]))
                            except ValueError:
                                # Rarely, a file will start with a match, but it's really just a random assortment of hex.
                                pass
                            except Exception as e:
                                print(device)
                                print(DATE_FORMAT_PATTERNS[device])
                                print(matches)
                                print(matches[0])
                                raise e
                    else:
                        log_action("Failed to extract any EXIF or find device match from %s" % file_path)
                        log_action("Exif: %s" % exif_dict)
                        meta["error"] = "❗Failed to extract any EXIF."
                        # raise e
            # print("extracted EXIF")
            # print(meta)

        else:
            if exif_gps_only:
                return meta

            device_found = False
            for device, r in DEVICE_REGEXES.items():
                matches = re.findall(r, meta["file_name"])
                if matches:
                    meta["device"] = device
                    device_found = True
                break

            for substring, device in DEVICE_SUBSTRINGS.items():
                if substring in file_path.split("/")[-1]:
                    meta["device"] = device
                    device_found = True
                    break

            if device_found:
                # print("found device: %s" % device)
                # We're just using the local time because we don't know. Try to parse it from the filename.
                if device in DATE_FORMAT_PATTERNS and device in DATE_PARSERS:
                    try:
                        matches = re.findall(DATE_PARSERS[device], meta["file_name"])
                        if matches:
                            parsed_time = datetime.datetime.strptime(matches[0], DATE_FORMAT_PATTERNS[device])
                            meta["datetime"] = parsed_time
                            log_action("Replaced datetime with known time parsing for %s: %s" % (device, meta["datetime"]))
                    except ValueError:
                        # Rarely, a file will start with a match, but it's really just a random assortment of hex.
                        pass
                    except Exception as e:
                        print(device)
                        print(DATE_FORMAT_PATTERNS[device])
                        print(matches)
                        print(matches[0])
                        raise e


        meta["mtime"] = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

        if "datetime" not in meta or not meta["datetime"]:
            # Try to parse out the date from the filename
            for device, pattern in DATE_FORMAT_PATTERNS.items():
                try:
                    matches = re.findall(DATE_PARSERS[device], meta["file_name"])
                    if matches:
                        parsed_time = datetime.datetime.strptime(matches[0], DATE_FORMAT_PATTERNS[device])
                        meta["datetime"] = parsed_time
                        log_action("Replaced datetime with known time parsing for %s: %s" % (device, meta["datetime"]))
                except ValueError:
                    # Rarely, a file will start with a match, but it's really just a random assortment of hex.
                    pass
                except Exception as e:
                    print(device)
                    print(DATE_FORMAT_PATTERNS[device])
                    print(matches)
                    print(matches[0])
                    raise e

        # That failed too?  Just use file modification time and hope for the best.
        if "datetime" not in meta or not meta["datetime"]:
            meta["datetime"] = meta["mtime"]

        # Device it was captured on
        if "Camera Model" in meta:
            if (
                meta["Camera Model"] in CAMERA_MODEL_MAPPINGS and
                meta["Camera Model"] is not None
            ):
                meta["device"] = CAMERA_MODEL_MAPPINGS[meta["Camera Model"]]
            else:
                camera_key = meta["Camera Model"].lower().replace(" ", "_")
                EXTRA_CAMERA_MAPPINGS[camera_key] = meta["Camera Model"]
                CAMERA_MODEL_MAPPINGS[meta["Camera Model"]] = camera_key
                DEVICE_DISPLAYNAME_MAPPINGS[camera_key] = meta["Camera Model"]
                meta["device"] = CAMERA_MODEL_MAPPINGS[meta["Camera Model"]]

        try:
            if meta["is_image"] and "width" not in meta:
                with Image.open(file_path) as im:
                    meta["width"], meta["height"] = im.size
                    meta["width"] = int(meta["width"])
                    meta["height"] = int(meta["height"])
        except UnidentifiedImageError:
            log_action("Failed to read image at %s. It might be corrupt, please check and try again." % file_path)
            meta["failed"] = "❗Failed to read image at %s. It might be corrupt, please check and try again."
            return meta

        meta["person"] = "steven"
        if "device" in meta and "edna" in meta["device"]:
            meta["person"] = "edna"

        date_str = "%s%s" % (
            meta["person"],
            meta["datetime"].strftime("%Y-%m-%d"),
        )
        month_str = "%s%s" % (
            meta["person"],
            meta["datetime"].strftime("%Y-%m"),
        )

        # Country of Capture
        opened = False
        # If it's missing and we can get it via EXIF GPS, do it.
        if (date_str in brain["date_country"] and date_str in brain["date_city"]):

            meta["country"] = brain["date_country"][date_str]
            brain["date_country"][date_str] = brain["date_country"][date_str]
            meta["city"] = brain["date_city"][date_str]
            brain["date_city"][date_str] = brain["date_city"][date_str]

        elif (
            (
                date_str not in brain["date_country"] or
                date_str not in brain["date_city"]
            ) and
            "lat" in meta and
            "lon" in meta
        ):
            retry = True
            while retry:
                print(" - Checking Online Reverse Geocode (%s%s).." % (meta["lat"], meta["lon"],))

                resp = requests.get(
                    "https://us1.locationiq.com/v1/reverse.php?key=%s&lat=%s&lon=%s&format=json" %
                    (
                        LOCATIONIQ_TOKEN,
                        meta["lat"],
                        meta["lon"],
                    ),
                    timeout=5
                )
                # print(resp.json())
                retry = False
                try:
                    city = None
                    if "country" in resp.json()["address"]:
                        country = resp.json()["address"]["country"]
                        if "city" in resp.json()["address"]:
                            city = resp.json()["address"]["city"]
                        elif "county" in resp.json()["address"]:
                            city = resp.json()["address"]["county"]

                        if "state" in resp.json()["address"]:
                            meta["state"] = resp.json()["address"]["state"]
                            brain["date_state"][date_str] = resp.json()["address"]["state"]
                            if not city:
                                city = meta["state"]

                        if not city:
                            print("found address, but no city:")
                            print(resp.json())
                        if country:
                            meta["country"] = country
                            brain["date_country"][date_str] = country
                        if city:
                            meta["city"] = city
                            brain["date_city"][date_str] = city
                except Exception as e:
                    print(resp.json())
                    if "error" in resp.json() and "Rate Limit" in resp.json()["error"]:
                        if resp.json()["error"] == "Rate Limited Day":
                            raise Exception("Geolocation rate-limited for today.  Either buy a subscription or wait until tomorrow.")
                        retry = True
                        time.sleep(15)
                        log_action("Rate limited.  Waiting 15 seconds...")
                    else:
                        log_action("Failed to parse json")
                        log_action(resp.json())
                        print(resp.json())

                        raise e

        if "device" not in meta or not meta["device"]:
            exif_camera = None
            if "Camera Model" in meta:
                exif_camera = meta["Camera Model"]
            error_str = "Couldn't find a matching device for %s. (Exif Camera: %s) Please update CAMERA_MODEL_MAPPINGS in the script." % (
                meta["file_name"],
                exif_camera,
            )
            log_action(error_str)
            if not ARGS.require_device and not exif_camera:
                meta["device"] = "unknown"
            else:
                print(meta)
                print(CAMERA_MODEL_MAPPINGS)
                print("Camera Model" in meta)
                print(meta["Camera Model"].strip() in CAMERA_MODEL_MAPPINGS)
                raise Exception(error_str)

        if date_str not in brain["date_country"]:
            if exif_gps_only:
                return meta

            pre_exif_location = pre_exif_date(date_str)
            if pre_exif_location:
                brain["date_country"][date_str] = pre_exif_location["country"]
                brain["date_city"][date_str] = pre_exif_location["city"]
                brain["date_state"][date_str] = pre_exif_location["state"]
                brain["month_country"][date_str] = pre_exif_location["country"]
                meta["country"] = pre_exif_location["country"]
                meta["city"] = pre_exif_location["city"]
                meta["state"] = pre_exif_location["state"]

            else:

                if meta["is_image"]:
                    os.system("open -a %s %s" % (
                        preview_path,
                        file_path.replace(" ", "\\ ").replace("(", "\\(").replace(")", "\\)"),
                    ))
                else:
                    os.system("open %s" % file_path.replace(" ", "\\ ").replace("(", "\\(").replace(")", "\\)"))

                previous = None
                for d in sorted(brain["date_country"].keys(), reverse=False):
                    # print("%s < %s  | %s" % (d, date_str, previous))
                    if d >= date_str:
                        if not previous:
                            previous = brain["date_country"][d]
                        break
                    previous = brain["date_country"][d]
                subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff", ])

                # Just for output
                if date_str in brain["date_city"]:
                    default_city = brain["date_city"][date_str]

                else:
                    default_city = None
                    # print("%s < %s  | City %s" % (d, date_str, previous))
                    for d in sorted(brain["date_city"].keys(), reverse=False):
                        if d >= date_str:
                            if not default_city:
                                default_city = brain["date_city"][d]
                            break
                        default_city = brain["date_city"][d]

                if default_city:
                    input_str = "\n   %s, what country is this from, on %s? [%s, %s] " % (
                        meta["person"].title(),
                        meta["datetime"].strftime("%B %d, %Y"),
                        default_city,
                        previous,
                    )
                else:
                    input_str = "\n   %s, what country is this from, on %s? [%s] " % (
                        meta["person"].title(),
                        meta["datetime"].strftime("%B %d, %Y"),
                        previous,
                    )

                country = input(input_str).strip()
                if not country:
                    country = previous
                meta["country"] = country
                brain["date_country"][date_str] = meta["country"]
                opened = True

        # City of Capture
        if "city" not in meta or not meta["city"]:
            if exif_gps_only:
                return meta
            if date_str in brain["date_city"]:
                meta["city"] = brain["date_city"][date_str]
            else:
                if not opened:
                    os.system("open %s" % file_path.replace(" ", "\\ "))
                    opened = True

                previous = None
                # print("%s < %s  | City %s" % (d, date_str, previous))
                for d in sorted(brain["date_city"].keys(), reverse=False):
                    if d >= date_str:
                        if not previous:
                            previous = brain["date_city"][d]
                        break
                    previous = brain["date_city"][d]
                subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff", ])
                city = input("   %s, what city is this from, on %s? [%s] " % (
                    meta["person"].title(),
                    meta["datetime"].strftime("%B %d, %Y"),
                    previous,
                )).strip()
                if not city:
                    city = previous
                meta["city"] = city
                brain["date_city"][date_str] = meta["city"]

        if meta["country"] in USA_NAMES and meta["datetime"].year < 2014 and "state" not in meta:
            if date_str in brain["date_state"]:
                meta["state"] = brain["date_state"][date_str]
            else:
                brain["date_state"][date_str] = "Adding.."
                previous = None
                for d in sorted(brain["date_state"].keys(), reverse=False):
                    if d >= date_str:
                        if not previous:
                            previous = brain["date_state"][d]
                        break
                    previous = brain["date_state"][d]

                subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff", ])
                state = input("   %s, what state is this from, on %s? [%s] " % (
                    meta["person"].title(),
                    meta["datetime"].strftime("%B %d, %Y"),
                    previous,
                )).strip()
                if not state:
                    state = previous
                meta["state"] = state
                brain["date_state"][date_str] = state

        for needle, replacement in COUNTRY_REPLACEMENTS.items():
            meta["country"] = meta["country"].replace(needle, replacement)
        meta["country"] = meta["country"].strip()

        if "state" in meta:
            for needle, replacement in CITY_REPLACEMENTS.items():
                meta["state"] = meta["state"].replace(needle, replacement)
            meta["state"] = meta["state"].strip()

        if meta["country"] in COUNTRY_MAPPINGS:
            meta["country"] = COUNTRY_MAPPINGS[meta["country"]]

        if meta["country"] in USA_NAMES and meta["datetime"].year < 2014:
            if month_str not in brain["month_country"]:
                brain["month_country"][month_str] = [meta["state"], ]
            elif meta["state"] not in brain["month_country"][month_str]:
                brain["month_country"][month_str].append(meta["state"])

        else:
            if month_str not in brain["month_country"]:
                brain["month_country"][month_str] = [meta["country"], ]
            elif meta["country"] not in brain["month_country"][month_str]:
                brain["month_country"][month_str].append(meta["country"])

        if brain["date_city"][date_str] in CITY_MAPPINGS:
            brain["date_city"][date_str] = CITY_MAPPINGS[brain["date_city"][date_str]]

        if meta["city"] is None:
            meta["city"] = UNKNOWN_PLACE_NAME
        else:
            for needle, replacement in CITY_REPLACEMENTS.items():
                meta["city"] = meta["city"].replace(needle, replacement)
            meta["city"] = meta["city"].strip()

        if meta["city"] in CITY_MAPPINGS:
            meta["city"] = CITY_MAPPINGS[meta["city"]]

        # 2016  / 03 - Argentina, Colombia  / 16 - Medellin  / 2016-01-03_10-55-22_dragonfly_medellin_colombia_IMG_12343.JPG
        # 2019/10 - Japan, Poland/ 20 - Tokyo  / 2019-10-20_09-55-12_haetori_tokyo_japan_DJI_0727.MP4
        # 2019 /12 - Japan, New Zealand /16 - Auckland/2019-12-16_15-32-43_pocket_auckland_new-zealand_DJI_1234.MP4
        meta["datetimestr"] = "%s_%02d-%02d-%02d" % (
            meta["datetime"].strftime("%Y-%m-%d"),
            meta["datetime"].hour,
            meta["datetime"].minute,
            meta["datetime"].second,
        )
        meta["mtimestr"] = "%s_%02d-%02d-%02d" % (
            meta["mtime"].strftime("%Y-%m-%d"),
            meta["mtime"].hour,
            meta["mtime"].minute,
            meta["mtime"].second,
        )
        # Detect if it's already one we've sorted
        needed_cleanup = False
        meta["cleaned_name"] = meta["file_name"]
        for substring, dev in DEVICE_SUBSTRINGS.items():
            if "_%s_" % dev in meta["file_name"]:
                meta["cleaned_name"] = meta["cleaned_name"].replace("_%s" % dev, "")
                needed_cleanup = True
        if meta["mtimestr"] in meta["cleaned_name"]:
            meta["cleaned_name"] = meta["cleaned_name"].replace("_%s" % meta["mtimestr"], "")
            needed_cleanup = True

        # Do cleanup on ones that were somehow mucked up.
        if needed_cleanup:
            meta['cleaned_name'] = re.sub(r"\A%s-\d\d-\d\d_\d\d-\d\d-\d\d_" % meta["datetime"].year, '', meta['cleaned_name'])

        meta["person"] = "steven"
        if "edna" in meta["device"]:
            meta["person"] = "edna"

        meta["canonical_name"] = "%(datetimestr)s_%(device)s_%(city)s_%(country)s__%(cleaned_name)s" % meta
        meta["canonical_path"] = os.path.join(
            meta["person"],
            "%s" % meta["datetime"].year,
            "%02d - %s" % (meta["datetime"].month, ", ".join(brain["month_country"][month_str])),
            "%02d - %s" % (meta["datetime"].day, brain["date_city"][date_str]),
        )

        meta["lowest_distance"] = None
        meta["lowest_distance_from"] = None
        if not exif_gps_only:
            if meta["is_image"]:
                try:
                    meta["imagehashes"] = image_hashes(file_path)

                    lowest_distance = 9999999
                    lowest_hash = None
                    for ih in brain["imagehashes"]:
                        if not ih.startswith("file"):
                            # print(ih)
                            # print(meta["imagehash"])
                            for rotation_hash in meta["imagehashes"]:
                                try:
                                    distance = photohash.hash_distance(rotation_hash, ih)
                                    # print("   %s - %s - %s" % (ih, brain["imagehashes"][ih]["relative_file_path"], distance))
                                    if distance < lowest_distance:
                                        lowest_distance = distance
                                        lowest_hash = ih
                                        meta["lowest_distance_from"] = brain["imagehashes"][ih]["relative_file_path"]
                                        meta["lowest_distance"] = lowest_distance
                                except Exception as e:
                                    print("\n\n\nerror comparing hashes")
                                    print(rotation_hash)
                                    print(meta)
                                    print("\n")
                                    print(ih)
                                    print(brain["imagehashes"][ih])
                                    print("\n\ndone")
                                    raise e

                    log_action(meta)
                    if lowest_hash:
                        lowest_hash_image = brain["imagehashes"][lowest_hash]

                        current_image_longest_edge = int(meta["width"])
                        if int(meta["height"]) > int(meta["width"]):
                            current_image_longest_edge = int(meta["height"])
                        hash_image_longest_edge = int(lowest_hash_image["width"])
                        if int(lowest_hash_image["height"]) > int(lowest_hash_image["width"]):
                            hash_image_longest_edge = int(lowest_hash_image["height"])
                    # print(meta["lowest_distance"])
                    # print(lowest_hash)
                    # if meta["imagehash"] in brain["imagehashes"]:
                    if (
                        (lowest_distance < MAXIMUM_IDENTICAL_HASH_DISTANCE and current_image_longest_edge == hash_image_longest_edge) or
                        (lowest_distance < MAXIMUM_THUMBNAIL_HASH_DISTANCE and current_image_longest_edge != hash_image_longest_edge)
                    ):
                        # Orientations
                        if current_image_longest_edge > hash_image_longest_edge:
                            dup_file_path = lowest_hash_image["relative_file_path"]
                            # Clear all matching hashes
                            for hash_to_delete in brain["imagehashes"][lowest_hash]["imagehashes"]:
                                try:
                                    del brain["imagehashes"][hash_to_delete]
                                except:
                                    log_action("Failed to delete imagehash %s. Ignoring and continuing, but that's weird." % hash_to_delete)

                            meta["result"] = "valid"
                            meta["original"] = meta["relative_file_path"]
                            log_action("Added %s to the list of files and removed lower-resolution duplicate %s" % (
                                meta["relative_file_path"],
                                dup_file_path,
                            ))
                            meta["replaced"] = dup_file_path

                            for rotation_hash in meta["imagehashes"]:
                                brain["imagehashes"][rotation_hash] = meta
                        else:
                            log_action("Skipping, image match: \n     %s with\n     %s (already added)" % (
                                meta["relative_file_path"],
                                lowest_hash_image["relative_file_path"],
                            ))
                            meta["result"] = "duplicate"
                            meta["original"] = lowest_hash_image["relative_file_path"]
                    else:
                        for rotation_hash in meta["imagehashes"]:
                            brain["imagehashes"][rotation_hash] = meta
                        meta["result"] = "valid"
                        log_action("Added %s to the list of files. (%s)" % (
                            meta["relative_file_path"],
                            meta["imagehashes"],
                        ))
                except Exception as e:
                    log_action("Failed to imagehash %s. Falling back to file hash." % meta["relative_file_path"])
                    try:
                        log_action(traceback.format_exc())
                    except:
                        pass
                    # raise e

            if "imagehashes" not in meta:
                meta["filesize"] = os.path.getsize(meta["file_path"])
                namesize_hash = "file%s" % meta["filesize"]
                if namesize_hash in brain["imagehashes"]:
                    # File size match. We're going to have to compare MD5s
                    if "md5" not in brain["imagehashes"][namesize_hash]:
                        brain["imagehashes"][namesize_hash]["md5"] = md5_file(brain["imagehashes"][namesize_hash]["file_path"])

                    meta["md5"] = md5_file(meta["file_path"])

                    if meta["md5"] != brain["imagehashes"][namesize_hash]["md5"]:
                        # We have mismatching files.
                        namesize_hash = "file%s__%s" % (meta["md5"], meta["filesize"],)
                        brain["imagehashes"][namesize_hash] = meta
                        meta["result"] = "valid"
                        log_action("Added %s to the list of files." % meta["relative_file_path"])
                    else:
                        # Check and choose the older file.
                        if meta["mtime"] < brain["imagehashes"][namesize_hash]["mtime"]:
                            brain["imagehashes"][namesize_hash] = meta
                            meta["result"] = "valid"
                            log_action("Added %s to the list of files." % meta["relative_file_path"])
                        else:
                            meta["result"] = "duplicate"
                            meta["original"] = brain["imagehashes"][namesize_hash]["relative_file_path"]
                            log_action("Skipping, file match: \n     %s, with\n     %s (already added)" % (
                                meta["relative_file_path"],
                                brain["imagehashes"][namesize_hash]["relative_file_path"],
                            ))
                else:
                    brain["imagehashes"][namesize_hash] = meta
                    meta["result"] = "valid"
                    log_action("Added %s to the list of files." % meta["relative_file_path"] )

        return meta


    def parse_file_list(source_dir, file_list, exif_gps_only=True):
        global IMPORT_DIR
        if len(file_list) > 0 and "no such file or directory" not in file_list[0].lower():
            counter = 1
            total = len(file_list)
            total_size = 0
            size_copied = 0
            start_time = datetime.datetime.now()
            for file_path in file_list:
                if not ignored(file_path):
                    total_size += os.path.getsize(file_path)

            for file_path in file_list:
                write_temp_brain()
                meta = None
                if not ignored(file_path) and os.path.getsize(file_path) > 0:

                    sys.stdout.write("\r Checking %s... (%s/%s)" % (
                        file_path.split("/")[-1], counter, total,
                    ))
                    sys.stdout.flush()
                    meta = get_file_metadata(file_path, exif_gps_only=exif_gps_only)
                    # print(meta)
                    if "failed" in meta:
                        action = "❗Failed: %s" % meta["failed"]
                    elif exif_gps_only:
                        if "error" in meta:
                            action = "❗Checked"
                        else:
                            action = "✔ Checked"
                    elif "result" in meta and meta["result"] == "valid":
                        if "replaced" in meta:
                            action = "✔ Replaced %s with" % meta["replaced"]
                        else:
                            action = "✔ Added"
                    else:
                        # print(meta)
                        if (
                            "lowest_distance" in meta and 
                            meta["lowest_distance"] is not None and
                            "original" in meta
                        ):
                            if meta["lowest_distance"] == 0:
                                action = "- Duplicate of %s: (Image match: Exact) " % (
                                    meta["original"],
                                )
                            else:
                                action = "- Duplicate of %s: (Image match: %s distance) " % (
                                    meta["original"],
                                    meta["lowest_distance"],
                                )
                        else:
                            action = "- Duplicate of %s: (File match) " % (
                                meta["original"],
                            )

                    if (exif_gps_only and meta["is_image"]) or not exif_gps_only:
                        country_str = "Unknown"
                        if "country" in meta:
                            country_str = meta["country"]
                        city_str = "Unknown"
                        if "city" in meta and meta["city"] is not None:
                            city_str = meta["city"]

                        error_str = ""
                        if "error" in meta:
                            error_str = meta["error"]
                        try:
                            if "failed" not in meta:
                                if exif_gps_only and (country_str == "Unknown" or city_str == "Unknown"):
                                    sys.stdout.write("\r%s %s. %s (%s) %s\n" % (
                                        action,
                                        meta["relative_file_path"],
                                        DEVICE_DISPLAYNAME_MAPPINGS[meta["device"]],
                                        meta["device"],
                                        error_str,
                                    ))
                                else:
                                    sys.stdout.write("\r%s %s. %s (%s) from %s, %s %s\n" % (
                                        action,
                                        meta["relative_file_path"],
                                        DEVICE_DISPLAYNAME_MAPPINGS[meta["device"]],
                                        meta["device"],
                                        city_str,
                                        country_str,
                                        error_str,
                                    ))

                                if not exif_gps_only and (country_str == "Unknown" or city_str == "Unknown"):
                                    print(meta)
                                    pass
                            else:
                                sys.stdout.write("\r%s %s\n" % (
                                    action,
                                    meta["relative_file_path"],
                                ))
                        except Exception as e:
                            print(meta)
                            print(meta["device"])
                            raise e
                    else:
                        sys.stdout.write("\r%s %s. (Non-image or no GPS EXIF.)\n" % (
                                action,
                                meta["relative_file_path"],
                        ))
                    sys.stdout.flush()
                else:
                    if exif_gps_only:
                        if meta:
                            print("x Ignored %s" % meta["relative_file_path"])
                        else:
                            print("x Ignored %s" % file_path)

                    pass
                counter += 1
        else:
            print("❌ %s empty or not found." % (source_dir,))


    def copy_files(imagehash_list, dry_run=False):
        counter = 1
        total = len(imagehash_list.keys())
        total_size = 0
        size_copied = 0
        start_time = datetime.datetime.now()
        files_to_copy = []
        files_copied = []
        for imagehash, meta in imagehash_list.items():
            if not ignored(meta["file_path"]) and meta["file_path"] not in files_to_copy:
                total_size += os.path.getsize(meta["file_path"])
                files_to_copy.append(meta["file_path"])

        for imagehash, meta in imagehash_list.items():
            if not ignored(meta["file_path"]) and meta["file_path"] not in files_copied:
                file_path = meta["file_path"]
                current_file_size = os.path.getsize(file_path)
                sys.stdout.write("\r Checking %s... (%s/%s) %s/%s (%.1f %%) %s ETA" % (
                    meta["relative_file_path"], counter, total,
                    sizeof_fmt(size_copied), sizeof_fmt(total_size),
                    (100 * size_copied / total_size),
                    eta(start_time, size_copied, total_size)
                ))
                sys.stdout.flush()

                date_str = "%s%s" % (
                    meta["person"],
                    meta["datetime"].strftime("%Y-%m-%d"),
                )
                month_str = "%s%s" % (
                    meta["person"],
                    meta["datetime"].strftime("%Y-%m"),
                )
                updated_canonical_path = os.path.join(
                    "%s" % meta["datetime"].year,
                    "%02d - %s" % (meta["datetime"].month, ", ".join(brain["month_country"][month_str])),
                    "%02d - %s" % (meta["datetime"].day, brain["date_city"][date_str]),
                )
                file_import_dir = os.path.join(IMPORT_DIR, updated_canonical_path)
                pathlib.Path(file_import_dir).mkdir(parents=True, exist_ok=True)
                dest_file = os.path.join(file_import_dir, meta["canonical_name"])

                if not os.path.isfile(dest_file) or os.path.getsize(file_path) != os.path.getsize(dest_file):
                    sys.stdout.write("\r Importing %s... (%s/%s) %s/%s (%.1f %%) %s ETA" % (
                        meta["relative_file_path"], counter, total,
                        sizeof_fmt(size_copied), sizeof_fmt(total_size),
                        (100 * size_copied / total_size),
                        eta(start_time, size_copied, total_size),
                    ))
                    sys.stdout.flush()
                    import_file(file_path, dest_file, dry_run=dry_run)

                    sys.stdout.write("\r✔ Imported %s... (%s/%s) %s/%s (%.1f %%) %s ETA\n" % (
                        meta["relative_file_path"], counter, total,
                        sizeof_fmt(size_copied), sizeof_fmt(total_size),
                        (100 * size_copied / total_size),
                        eta(start_time, size_copied, total_size),
                    ))
                    sys.stdout.flush()
                    counter += 1
                else:
                    sys.stdout.write("\r✔ Previously imported %s... (%s/%s) %s/%s (%.1f %%) %s ETA\n" % (
                        meta["relative_file_path"], counter, total,
                        sizeof_fmt(size_copied), sizeof_fmt(total_size),
                        (100 * size_copied / total_size),
                        eta(start_time, size_copied, total_size),
                    ))
                    sys.stdout.flush()
                    counter += 1
                size_copied += current_file_size
                files_copied.append(meta["file_path"])


    def pull_files(args):
        print("\nImporting from %s..." % args.source_dir)

        # Get default Camera images
        if os.path.isdir(args.source_dir):
            sys.stdout.write("\nGetting file list...")
            file_list = get_local_file_list(args.source_dir)
            sys.stdout.write("done.\n")
            sys.stdout.flush()

            log_action("\nChecking for EXIF-based GPS information, and auto-tagging dates.")
            print("\nChecking for EXIF-based GPS information, and auto-tagging dates....")
            parse_file_list(args.source_dir, file_list, exif_gps_only=True)
            
            log_action("\nChecking for duplicates, verifying location, and deciding on the canonical copy.")
            print("\nChecking for duplicates, verifying location, and deciding on the canonical copy....")
            parse_file_list(args.source_dir, file_list, exif_gps_only=False)

            log_action("\nCopying files.")
            print("\nCopying files...")
            copy_files(brain["imagehashes"], dry_run=args.dry_run)


    def write_import_log():
        with open('import-%s.log' % now_str, "w+") as f:
            f.write(action_log)
            if EXTRA_CAMERA_MAPPINGS != {}:
                f.write("\n Autogenerated Missing Camera Mappings:")
                print("\n Autogenerated Missing Camera Mappings:")
                for key, model in EXTRA_CAMERA_MAPPINGS.items():
                    f.write("%s - %s" % (key, model))
                    print("%s - %s" % (key, model))
            print(" - import-%s.log" % now_str)


    def write_travel_history():
        for p in PEOPLE:
            travel_history = "Travel History, from my Photos\n"
            previous_city = None
            previous_country = None
            previous_date = None
            second_previous_city = None
            second_previous_country = None
            second_previous_date = None

            travel_history_csv = "Year, Month, Day, Country, City, Days\n"
            for date in sorted(brain["date_country"].keys()):
                country = brain["date_country"][date]
                city = brain["date_city"][date]
                if not city:
                    city = ""
                non_person_date = date
                for replace_p in PEOPLE:
                    non_person_date = non_person_date.replace(replace_p, "")
                parsed_date = datetime.datetime.strptime(non_person_date, "%Y-%m-%d")

                if city != previous_city or country != previous_country:
                    if previous_date and second_previous_date:
                        days = (previous_date - second_previous_date).days
                    else:
                        days = 0

                    travel_history += "%s - %s, %s (%s days)\n" % (date, city, country, days)
                    travel_history_csv += "%s, %s, %s, %s, %s, %s\n" % (
                        int(non_person_date.split("-")[0]),
                        int(non_person_date.split("-")[1]),
                        int(non_person_date.split("-")[2]),
                        country.replace(",", "\\,"),
                        city.replace(",", "\\,"),
                        days,
                    )
                    second_previous_city = previous_city
                    second_previous_country = previous_country
                    second_previous_date = previous_date
                    previous_city = city
                    previous_country = country
                    previous_date = parsed_date

            with open('%s-travel-history-%s.log' % (p, now_str), "w+") as f:
                f.write(travel_history)
                print(" - travel-history-%s.log" % now_str)

            with open('%s-travel-history-%s.csv' % (p, now_str), "w+") as f:
                f.write(travel_history_csv)
                print(" - travel-history-%s.csv" % now_str)

    def cli():
        global ARGS
        # print(photohash.hash_distance("e5a6a6e5a4a4e5a7", "1a58dada189a9a58"))
        # return

        parser = argparse.ArgumentParser(description='Importer project')
        parser.add_argument('source_dir', metavar='source_dir', type=str, help='What directory to import from?')
        parser.add_argument('destination', metavar='destination', type=str, help='What volume to import to? e.g. ./output/')
        parser.add_argument(
            '--keep-history', action='store_true',
            help="Keep import history."
        )
        parser.add_argument(
            '--clear-locations', action='store_true',
            help="Clear location-date associations."
        )
        parser.add_argument(
            '--all_files', action='store_true',
            help="Attempt all files, not just images, movies, and music."
        )
        parser.add_argument(
            '--require-device', action='store_true',
            help="Do not allow devices to be set to 'unknown' if we can't figure it out.  Throw an error."
        )

        parser.add_argument(
            '--dry-run', action='store_true',
            help="Run through all steps, but don't copy - just output the log."
        )

        args = parser.parse_args()
        # print(args)
        if args.keep_history:
            print("✔ Keeping History.")
            pass
        else:
            print("✔ Clearing History.")
            brain["imagehashes"] = {}

        if args.clear_locations:
            print("✔ Clearing Locations.")
            brain["date_country"] = {}
            brain["date_city"] = {}
            brain["date_state"] = {}
            brain["month_country"] = {}

        args.full_source_path = os.path.abspath(args.source_dir)
        ARGS = args

        prepare_import_dir(args)
        pull_files(args)

        print("\nFinished import for %s" % args.source_dir)
        # walk_tree(args)

        print("\nCleaning up.")
        print("✔ Saving brain.")
        with open('importamator.db', "w+b") as f:
            pickle.dump(brain, f)

        print("✔ Creating Reports.")
        write_import_log()
        write_travel_history()

        print("\nImport and deduplication for %s complete." % args.source_dir)

    if __name__ == '__main__':
        cli()
except Exception as e:
    print("Exception caught, saving brain so far.")
    with open('importamator.db', "w+b") as f:
        pickle.dump(brain, f)


        print("Creating Reports.")
        write_import_log()
        write_travel_history()


    raise e
