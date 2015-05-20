

global WIKITEXT, JSON
global PAGE_INDEX, REVISION_INDEX

import gzip as zip
import os, json, csv, re, atexit
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

def _pick_dir(cleaned):
    cleaned = [c.upper() for c in cleaned if c.isalnum()]
    return tuple([cleaned[i] for i in range(min(len(cleaned), dir_nesting))])

cleaner = re.compile(r"[^\(\)\-\_\.\s\w\d]|^[^\w\d]")
def _clean_title(title):
    clean = cleaner.sub("_", unidecode(title).strip())[:200]
    if clean.lower() in disallowed_filenames:
        clean = disallowed_filenames[clean.lower()]
    return _pick_dir(clean), clean

def _pick_path(title, ext):
    dirs, cleaned = _clean_title(title)
    return os.path.join(os.path.join(root_dir, *dirs), "%s.%s" % (cleaned, ext))


index_num = None
index = None
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
def _write_page(title, type, content, overwrite=False):
    global known_good_dirs
    path = _pick_path(title, type)
    if index is not None:
        global index, index_num
        index.write('%d:["%s","%s"],' % (index_num, title, path))
        index_num += 1
    if not overwrite and os.path.exists(path):
        return
    dirs_path = os.path.dirname(path)
    if dirs_path not in known_good_dirs and not os.path.exists(dirs_path):
        os.makedirs(dirs_path)
    known_good_dirs.add(dirs_path)
    zip.open(path, "wb").write(bytes(content, 'UTF-8'))

def write_wikitext(title, content, overwrite=False):
    _write_page(title, WIKITEXT, content, overwrite)

def write_json(title, content, overwrite=False):
    _write_page(title, JSON, content, overwrite)


def _read_page(title, type):
    path = _pick_path(title, type)
    if(os.path.isfile(path)):
        return zip.open(path, "rb").read()
    else:
        return None

def _fetch_wikitext(title):
    import urllib.parse
    import urllib.request as url
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
        # Launch gateway server
        wikitojson = subprocess.Popen(["java", "-jar", "./WikiToJson.jar"], stdout=subprocess.PIPE, universal_newlines=True)
        atexit.register(wikitojson.terminate)
        wikitojson.stdout.read() # Wait until the gateway has launched
        gateway = java().wikitextToJson
    return gateway

def _parse_wikitext_to_json(wikitext):
    return initialize_wikiparser()(wikitext)

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
            write_json(title, res_json)
            return res_json
        else:
            return None