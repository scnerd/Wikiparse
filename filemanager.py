

global WIKITEXT, JSON
global PAGE_INDEX, REVISION_INDEX

import gzip as zip
import os, json, re, atexit, itertools
from unidecode import unidecode

WIKITEXT = "wtxt"
JSON = "json"

config = json.load(open("config.json"))
root_dir = config['cache_dir']
PAGE_INDEX = os.path.join(root_dir, config['page_index'])
PAGE_INDEX_RAW = PAGE_INDEX.rpartition(".")[0] + ".json"
#REVISION_INDEX = config['revision_index']
disallowed_filenames = config['disallowed_file_names']

dir_nesting = config['dir_nesting']

global index, index_num
index_num = None
index = None

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
    cleaned = _clean_title(partial_title).lower()
    dir = os.path.join(root_dir, *_pick_dir(cleaned))
    for dirpath, dirnames, filenames in os.walk(dir):
        filenames = list(filenames)
        yield from (f.rpartition('.')[0] if '.' in f else f for f in filenames if f.lower().startswith(cleaned))

def _pick_path(title, ext):
    cleaned = _clean_title(title)
    dirs = _pick_dir(cleaned)
    return os.path.join(os.path.join(root_dir, *dirs), "%s.%s" % (cleaned, ext))

def start_recording_index():
    global index, index_num
    index = open(PAGE_INDEX_RAW, "w", 1000000)
    index.write("{")
    index_num = 1
    atexit.register(finish_recording_index)

def finish_recording_index():
    global index, index_num
    index.write('-1:["",""]}')
    index.flush()
    index.close()
    with open(PAGE_INDEX_RAW, 'rb') as raw:
        with zip.open(PAGE_INDEX, 'wb') as zipper:
            while True:
                data = raw.read(1000000)
                if not data:
                    break
                zipper.write(data)
    os.remove(PAGE_INDEX_RAW)
    #zip.open(PAGE_INDEX, 'wb').write(json.dumps({i: index[i] for i in range(len(index))}))

def read_index():
    return json.loads(zip.open(PAGE_INDEX, 'rb').read())

known_good_dirs = set()
def _write_page(title, page_type, content, overwrite=False):
    global known_good_dirs, index, index_num
    path = _pick_path(title, page_type)
    _verbose("Writing to %s" % path)
    if index is not None:
        index.write('%d:["%s","%s"],' % (index_num, title, path))
        index_num += 1
    if not overwrite and os.path.exists(path):
        _verbose("File already exists, aborting write")
        return
    dirs_path = os.path.dirname(path)
    if dirs_path not in known_good_dirs and not os.path.exists(dirs_path):
        os.makedirs(dirs_path)
    known_good_dirs.add(dirs_path)
    zip.open(path, "wb").write(bytes(content, 'UTF-8') if type(content) is not bytes else content)

def write_wikitext(title, content, overwrite=False):
    _write_page(title, WIKITEXT, content, overwrite)

def write_json(title, content, overwrite=False):
    _write_page(title, JSON, content, overwrite)


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
    wikitext = url.urlopen(config['fetch_url'] % params).read()
    if config['cache_pulls']:
        write_wikitext(title, wikitext)
    return wikitext

gateway = None
def initialize_wikiparser():
    import subprocess, atexit
    from py4j.java_gateway import JavaGateway as java
    global gateway
    if gateway is None:
        _verbose("Launching gateway")
        # Launch gateway server
        wikitojson = subprocess.Popen(["java", "-jar", "./WikiToJson.jar"], stdout=subprocess.PIPE, universal_newlines=True)
        atexit.register(wikitojson.kill)
        wikitojson.stdout.read() # Wait until the gateway has launched
        _verbose("Gateway launched")
        gateway = java()
    return gateway

def _parse_wikitext_to_json(wikitext):
    _verbose("Converting wikitext to json")
    return initialize_wikiparser().convertWikitextToJson(wikitext)

def read_wikitext(title):
    ret = _read_page(title, WIKITEXT)
    if ret is not None:
        return ret
    elif config['try_pulls']:
        return _fetch_wikitext(title)
    else:
        return None

def read_json(title):
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