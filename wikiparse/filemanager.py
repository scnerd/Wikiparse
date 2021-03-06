'''
Manages all loading and caching of data for wikiparse.
This module is meant primarily for use within wikiparse,
but can be used from the outside to provide raw data or
aid in debugging.
   
.. moduleauthor:: David Maxson <jexmax@gmail.com>
'''

global WIKITEXT, JSON

import zipfile
import os, json, re, atexit
from unidecode import unidecode
import atexit

# http://stackoverflow.com/questions/842557/how-to-prevent-a-block-of-code-from-being-interrupted-by-keyboardinterrupt-in-py
import signal
import logging

class DelayedKeyboardInterrupt(object):
    def __enter__(self):
        self.signal_received = False
        self.old_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self.handler)

    def handler(self, signal, frame):
        self.signal_received = (signal, frame)
        logging.debug('SIGINT received. Delaying KeyboardInterrupt.')

    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, self.old_handler)
        if self.signal_received:
            self.old_handler(*self.signal_received)
           
# END SO CODE

WIKITEXT = "wtxt"
JSON = "json"

WIKIPARSE_DIR = os.path.dirname(__file__)

config = json.load(open(os.path.join(WIKIPARSE_DIR, "config.json")))
wd = os.getcwd()
os.chdir(WIKIPARSE_DIR)
archive_path = os.path.abspath(os.path.expanduser(config['cache_zip']))
os.chdir(wd)
text_encoding = config['encoding']
disallowed_filenames = config['disallowed_file_names']

global page_archive
page_archive = None
compression_levels = [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA]
compression = compression_levels[config['compression_level']]

def report():
    print("Archive has been closed properly")
def open_archive(mode):
    global page_archive
    if page_archive is not None:
        page_archive.close()
        atexit.unregister(report)
        atexit.unregister(page_archive.close)
    page_archive = zipfile.ZipFile(archive_path, mode, compression, allowZip64=True)
    atexit.register(report)
    atexit.register(page_archive.close)


if not os.path.exists(archive_path):
    # Creates skeleton archive
    open_archive('w')
open_archive('r')

def enable_writing():
    open_archive('a')

if config['verbose_filemanager']:
    def _verbose(txt):
        print(txt)
else:
    def _verbose(txt):
        pass

def possible_titles(partial_title=None, max_edit_distance=-1):
    '''Retrieves all cached pages starting with the specified title text.
    
    :param partial_title: The beginning of a title.
    :type partial_title: str
    :returns: A generator that provides the possible title names matching the specified title beginning
    :rtype: Generator of str
    '''
    if partial_title is not None:
        if max_edit_distance >= 0:
            from editdistance import eval as distance
            return (title for title in page_archive.namelist() if distance(title.lower().rpartition('.')[0], partial_title.lower()) <= max_edit_distance)
        else:
            return (title for title in page_archive.namelist() if title.startswith(partial_title))
    else:
        return page_archive.namelist()

def _pick_path(title, ext):
    return bytes(("%s.%s" % (title, ext)), text_encoding)

def _write_page(title, page_type, content, overwrite=False):
    # This prevents corruption of the zip file if the write is cancelled by a keyboard interrupt
    with DelayedKeyboardInterrupt():
        if content is None:
            return
        if page_archive.mode is not 'a':
            open_archive('a')
        path = _pick_path(title, page_type)
        _verbose("Writing to %s" % path)
        if not overwrite and path.decode(text_encoding) in page_archive.namelist():
            _verbose("Failed to write %s, file already exists (enable overwriting to dismiss this)" % title)
            return
        try:
            content = bytes(content, text_encoding) if type(content) is not bytes else content
        except TypeError as ex:
            print(str(ex))
            print("Tried to convert '%s' to 'bytes'" % str(type(content)))
        ftarget = path
        try:
            ftarget = page_archive.getinfo(path)
        except KeyError:
            pass
        page_archive.writestr(ftarget, content)

def write_wikitext(title, content, overwrite=False):
    '''Writes a wikitext page to its appropriate file

    :param title: The title of the page that is being written
    :type title: str
    :param content: The wikitext as a string
    :type content: str
    :param overwrite: Whether or not to overwrite the existing file if the file already exists
    :type overwrite: bool
    '''
    _write_page(title, WIKITEXT, content, overwrite)

def write_json(title, content, overwrite=False):
    '''Writes a json page to its appropriate file

    :param title: The title of the page that is being written
    :type title: str
    :param content: The json as a string
    :type content: str
    :param overwrite: Whether or not to overwrite the existing file if the file already exists
    :type overwrite: bool
    '''
    _write_page(title, JSON, content, overwrite)

def _read_page(title, type):
    path = _pick_path(title, type)
    _verbose("Reading from %s" % path)
    try:
        with DelayedKeyboardInterrupt():
            return str(page_archive.read(path), text_encoding)
    except KeyError:
        _verbose("Read failed, file does not exist")
        return None

def _fetch_wikitext(title):
    import urllib.parse
    import urllib.request as url
    _verbose("Pulling '%s' from wikipedia" % title)
    params = urllib.parse.urlencode({'action': 'raw', 'title': title})
    try:
        wikitext = str(url.urlopen(config['fetch_url'] % params).read(), text_encoding)
    except urllib.error.HTTPError:
        return None
    if config['cache_pulls']:
        write_wikitext(title, wikitext)
    return wikitext

gateway = None
def _initialize_wikiparser():
    import subprocess, atexit
    from py4j.java_gateway import JavaGateway as java
    global gateway
    if gateway is None:
        _verbose("Launching gateway")
        # Launch gateway server
        wikitojson = subprocess.Popen(["java", "-jar", os.path.join(WIKIPARSE_DIR, "WikiToJson.jar")], stdout=subprocess.PIPE, universal_newlines=True)
        atexit.register(wikitojson.kill)
        wikitojson.stdout.read() # Wait until the gateway has launched
        _verbose("Gateway launched")
        gateway = java()
    return gateway

def _parse_wikitext_to_json(wikitext):
    _verbose("Converting wikitext to json")
    return _initialize_wikiparser().convertWikitextToJson(wikitext)

def read_wikitext(title):
    '''Reads the wikitext for the specified page, fetching it directly from wikipedia if no cached version is available

    :param title: The name of the wikipedia page to retrieve wikitext for
    :type title: str
    :return: The wikitext
    :rtype: str
    '''
    ret = _read_page(title, WIKITEXT)
    if ret is not None:
        return ret
    elif config['try_pulls']:
        return _fetch_wikitext(title)
    else:
        return None

def read_json(title):
    '''Reads the json for the specified page, generating it with the parser from the wikitext if no cached version is available

    :param title: The name of the wikipedia page to retrieve json for
    :type title: str
    :return: The json text
    :rtype: str
    '''
    ret = _read_page(title, JSON)
    if ret is not None:
        return ret
    else:
        wikitext = read_wikitext(title)
        if wikitext is not None:
            res_json = _parse_wikitext_to_json(wikitext)
            if config['cache_pulls']:
                write_json(title, res_json)
            return res_json
        else:
            return None
