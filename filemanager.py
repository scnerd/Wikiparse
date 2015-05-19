

global WIKITEXT, JSON
global PAGE_INDEX, REVISION_INDEX

import gzip as zip
import os, json, csv
from unidecode import unidecode

WIKITEXT = "wtxt"
JSON = "json"

config = json.load(open("config.json"))
root_dir = config['cache_dir']
PAGE_INDEX = config['page_index']
REVISION_INDEX = config['revision_index']

dir_nesting = config['dir_nesting']

def _pick_dir(cleaned):
    return tuple([cleaned[i] if i < len(cleaned) else None for i in range(dir_nesting)])

def _clean_title(title):
    clean = unidecode(title)
    return _pick_dir(clean), clean

def _pick_path(title, ext):
    dirs, cleaned = _clean_title(title)
    return os.path.join(os.path.join(root_dir, *dirs), "%s.%s" % (cleaned, ext))


def _write_page(title, type, content):
    path = _pick_path(title, type)
    dirs_path = os.path.dirname(path)
    if not os.path.exists(dirs_path):
        os.makedirs(dirs_path)
    zip.open(path, "wb").write(content)

def write_wikitext(title, content):
    _write_page(title, WIKITEXT, content)

def write_json(title, content):
    _write_page(title, JSON, content)


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
            return _parse_wikitext_to_json(wikitext)
        else:
            return None