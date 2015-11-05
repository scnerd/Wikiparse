'''
Manages all loading and caching of data for wikiparse.
This module is meant primarily for use within wikiparse,
but can be used from the outside to provide raw data or
aid in debugging.
   
.. moduleauthor:: David Maxson <jexmax@gmail.com>
'''

global WIKITEXT, JSON
#global PAGE_INDEX, REVISION_INDEX

import gzip as zip
import os, json, re, atexit
from unidecode import unidecode

WIKITEXT = "wtxt"
JSON = "json"

WIKIPARSE_DIR = os.path.dirname(__file__)

config = json.load(open(os.path.join(WIKIPARSE_DIR, "config.json")))
root_dir = os.path.join(WIKIPARSE_DIR, config['cache_dir'])
#PAGE_INDEX = os.path.join(root_dir, config['page_index'])
#PAGE_INDEX_RAW = PAGE_INDEX.rpartition(".")[0] + ".json"
#REVISION_INDEX = config['revision_index']
disallowed_filenames = config['disallowed_file_names']

dir_nesting = config['dir_nesting']

global index, index_num
#index_num = None
#index = None

if config['verbose_filemanager']:
    def _verbose(txt):
        print(txt)
else:
    def _verbose(txt):
        pass

def _pick_dir(cleaned):
    cleaned = [c.upper() for c in cleaned if c.isalnum()]
    return tuple([cleaned[i] for i in range(min(len(cleaned), dir_nesting))])

cleaner = re.compile(r"[^\(\)\-\_\.\s\w\d]|^[^\w\d]")
def _clean_title(title):
    clean = cleaner.sub("_", unidecode(title).strip())[:200].lower()
    if clean in disallowed_filenames:
        clean = disallowed_filenames[clean.lower()]
    return clean

def possible_titles(partial_title):
    '''Retrieves all cached pages starting with the specified title text.
    
    :param partial_title: The beginning of a title.
    :type partial_title: str
    :returns: A generator that provides the possible title names matching the specified title beginning
    :rtype: Generator of str
    '''
    cleaned = _clean_title(partial_title)
    dir = os.path.join(root_dir, *_pick_dir(cleaned))
    for dirpath, dirnames, filenames in os.walk(dir):
        filenames = sorted(set(f.rpartition('.')[0] if '.' in f else f for f in filenames if f.lower().startswith(cleaned)))
        yield from filenames

def _pick_path(title, ext):
    cleaned = _clean_title(title)
    dirs = _pick_dir(cleaned)
    return os.path.join(os.path.join(root_dir, *dirs), "%s.%s" % (cleaned, ext))

def start_recording_index():
    '''When opening a wikipedia archive, this initializes the writing of the index file (not really used yet)
    '''
    #global index, index_num
    #index = open(PAGE_INDEX_RAW, "w", 1000000)
    #index.write("{")
    #index_num = 1
    #atexit.register(finish_recording_index)
    pass

def finish_recording_index():
    '''When opening a wikipedia archive, this finalizes the writing of the index file (not really used yet)
    '''
    #global index, index_num
    #index.write('-1:["",""]}')
    #index.flush()
    #index.close()
    #with open(PAGE_INDEX_RAW, 'rb') as raw:
    #    with zip.open(PAGE_INDEX, 'wb') as zipper:
    #        while True:
    #            data = raw.read(1000000)
    #            if not data:
    #                break
    #            zipper.write(data)
    #os.remove(PAGE_INDEX_RAW)
    #zip.open(PAGE_INDEX, 'wb').write(json.dumps({i: index[i] for i in range(len(index))}))
    pass

def read_index():
    '''Reads in the index file as a json object
    '''
    #return json.loads(zip.open(PAGE_INDEX, 'rb').read())
    pass

known_good_dirs = set()
def _write_page(title, page_type, content, overwrite=False):
    global known_good_dirs #, index, index_num
    path = _pick_path(title, page_type)
    _verbose("Writing to %s" % path)
    #if index is not None:
    #    index.write('%d:["%s","%s"],' % (index_num, title, path))
    #    index_num += 1
    if not overwrite and os.path.exists(path):
        _verbose("File already exists, aborting write")
        return
    dirs_path = os.path.dirname(path)
    if dirs_path not in known_good_dirs and not os.path.exists(dirs_path):
        os.makedirs(dirs_path)
    known_good_dirs.add(dirs_path)
    zip.open(path, "wb").write(bytes(content, 'UTF-8') if type(content) is not bytes else content)

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

def reset_page(title):
    '''Deletes any cached versions of the specified page so it can be updated when next requested

    :param title: The title of the page to delete
    '''
    for file_type in [WIKITEXT, JSON]:
        path = _pick_path(title, file_type)
        if os.path.exists(path):
            os.remove(path)


def _read_page(title, type):
    path = _pick_path(title, type)
    _verbose("Reading from %s" % path)
    if(os.path.isfile(path)):
        return str(zip.open(path, "rb").read(), 'UTF-8')
    else:
        _verbose("Read failed, file does not exist")
        return None

def _fetch_wikitext(title):
    import urllib.parse
    import urllib.request as url
    _verbose("Pulling '%s' from wikipedia" % title)
    params = urllib.parse.urlencode({'action': 'raw', 'title': title})
    try:
        wikitext = url.urlopen(config['fetch_url'] % params).read()
    except urllib.error.HTTPError:
        return None
    if config['cache_pulls']:
        write_wikitext(title, wikitext)
    return str(wikitext, 'UTF-8')

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
