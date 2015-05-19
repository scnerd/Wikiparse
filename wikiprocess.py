#!/usr/bin/env python3

'''
Processes the raw SQLite database, adding the more informative tables and entries as information is extracted
'''

'''
TODO:
Get reading/writing with the database working to the revisions table and from the pages table
Push data through java parser, save json and version to the database
Construct python-side modules for parsing the json into usable structures (?)
    - Cache these structures, or just the json?
Build loader that takes pages and pulls them, parsing through Java and Python as needed
'''

'''
FUTURE FEATURES:
Support redirections and disambiguations smoothly
Support live-fetching from wikipedia if the database is not downloaded and processed
'''

from xml.etree import ElementTree as ET
from py4j.java_gateway import JavaGateway as java
import sqlite3 as sql
import os, atexit, subprocess, json
from wikisplitter import DB_NAME

global config
config = json.load(open('config.json'))

VERSION = 1 # Increment when parsing the same json results in a different "parsed" datablock. -1 indicates not parsed

SQL_CREATE = r"CREATE TABLE revisions (page_id INTEGER, rev_number INTEGER, wikiparse_version INTEGER, json_zip BLOB, PRIMARY KEY (page_id, rev_number)); CREATE INDEX revisions_pid ON revisions (page_id);"
SQL_RETRIEVE_PAGE = r"SELECT id, title, xml_zip FROM pages WHERE title LIKE '?';"
SQL_NAME_CHECK = r"SELECT title FROM pages WHERE title LIKE '%?%';"
SQL_INSERT = r"INSERT INTO revisions (page_id, rev_number, parsed) VALUES (?,?,?);"

def initialize_sql(output_directory=config['db_directory']):
    path = os.path.join(output_directory, DB_NAME)
    initialize = False
    if not os.path.isfile(path):
        raise FileNotFoundError("The database must be initialized using 'wikisplitter.py' script before using wikiprocess")
    connection = sql.connect(path)
    atexit.register(connection.close)
    atexit.register(connection.commit)
    if initialize:
        cur = connection.cursor()
        cur.executescript(SQL_CREATE)
        connection.commit()
    return connection

global wikitojson
wikitojson = None
def initialize_wikiparser():
    global wikitojson
    if wikitojson is None:
        # Launch gateway server
        wikitojson = subprocess.Popen(["java", "-jar", "./WikiToJson.jar"], stdout=subprocess.PIPE, universal_newlines=True)
        atexit.register(wikitojson.terminate)
        wikitojson.stdout.read() # Wait until the gateway has launched

    return java() # Create new access to the gateway server (having multiple is ok, though not thread-safe)


def no_ns(tag):
    return tag.rpartition("}")[2] if "}" in tag else tag

def easy_parse(xml):
    data = [(no_ns(el.tag),
             (el.text.strip()
              if len(list(el)) == 0 else
              [('__body', el.text.strip())] + easy_parse(el)))
            for el in xml]
    return {tag1: [value2 for tag2, value2 in data if tag1 == tag2] for tag1, value1 in data}


class PageVersion(object):
    def __init__(self, parent, revision):
        # Receives a single page version's json format
        self.parent = parent
        self.revision = revision
        self.loaded = False

    def __getattribute__(self, item):
        if object.__getattribute__(self, 'loaded') or item in ['__getattribute__', 'loaded', 'load']:
            return object.__getattribute__(self, item)
        self.loaded = True # enables doing property lookups, so be careful in load method
        self.load()
        return self.__getattribute__(item)

    def load(self):
        parser = initialize_wikiparser()


class WikiPage(object):
    def __init__(self, name, cursor=None, force_reload=False):
        # Responsible to get to an array of JSON for each revision.
        #   Load revision json's from revision table, if not force_reload
        #   If no revisions loaded (none available, or force_reload),
        #       Load xml from pages table
        #       If no xml loaded, fail
        #       Get wikitexts out of xml
        #       Parse wikitexts into json
        #   Pass jsons into Revision class to get turned into usable page objects

        cursor = cursor if cursor is not None else initialize_sql(config['db_directory'])



        self.title = parsed['title'][0]
        self.revisions = [PageVersion(self, revision) for revision in parsed['revision']]
        self.cur_revision = self.revisions[-1]

    def __getattr__(self, item):
        return self.cur_revision.__getattribute__(item)

    def __setattr__(self, key, value):
        raise AttributeError("Cannot set attributes of a parsed wiki page")

    @classmethod
    def check_name(cls, name):
        cursor = initialize_sql(config['db_directory'])
        cursor.execute(SQL_NAME_CHECK, name)
        return [res['title'] for res in cursor.fetchall()]

    @classmethod
    def _get_page_id(cls, name, cursor):
        pass

    @classmethod
    def _load_jsons_from_table(cls, id, cursor):
        pass

    @classmethod
    def _load_xml_from_table(cls, id, cursor):
        pass

    @classmethod
    def _extract_wikitext_from_xml(cls, xml):
        pass

    @classmethod
    def _parse_json_from_wikitext(cls, gateway, wikitext):
        pass

def load_pages(names, force_reload=False, db_directory = "./wikipedia"):
    cursor = initialize_sql(db_directory)
    to_return = [WikiPage(name, cursor, force_reload) for name in names]
    for page in to_return: page.load();
    cursor.commit()
    cursor.close()
