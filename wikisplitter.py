#!/usr/bin/env python3

DB_NAME = "wikipedia.sqlite"

import os, gzip, argparse, sys, re
from xml.etree import ElementTree as ET
import atexit
from unidecode import unidecode
from time import time

global args

SQL_CREATE = r"CREATE TABLE pages (id INTEGER PRIMARY KEY, title TEXT, xml_zip BLOB);"
SQL_INSERT = r"INSERT INTO pages (title, xml_zip) VALUES (?,?);"

atexit.register(lambda: print("wikisplitter has closed gently"))
import sqlite3 as sql
def initialize_sql(output_directory):
    global args
    path = os.path.join(output_directory, DB_NAME)
    initialize = False
    if not os.path.isfile(path):
        initialize = True
    connection = sql.connect(path)
    atexit.register(connection.close)
    atexit.register(connection.commit)
    if initialize:
        cur = connection.cursor()
        cur.execute(SQL_CREATE)
        connection.commit()
    return connection

cleaner = re.compile(r"[^\(\)\-\_\.\s\w\d]|^[^\w\d]")

def normalize_title(title):
    return cleaner.sub("_", unidecode(title).strip())

def split_xml(xml_stream):
    num = 0
    prev_time = 0

    cursor = initialize_sql(args.output)
    commit_queue = []
    def push():
        nonlocal commit_queue
        cursor.executemany(SQL_INSERT, commit_queue)
        cursor.commit()
        commit_queue = []
    def output_page(title, page):
        nonlocal commit_queue
        commit_queue.append((title, gzip.compress(page)))
        if len(commit_queue) >= args.commit:
            push()

    for title, page in find_pages(xml_stream):
        num += 1
        if args.verbose:
            print(title)
        else:
            if time() - prev_time >= .1:
                prev_time = time()
                #tr.print_diff()
                #print(num)
                sys.stdout.write("%d\r" % num)
                sys.stdout.flush()
        output_page(title, page)
    push()
    cursor.close()


def find_pages(xml_stream):
    unknown_index = 0
    def title_finder(page_element):
        nonlocal unknown_index
        for el in list(page_element): # Children of this element
            if el.tag.rpartition('}')[2] == 'title':
                return normalize_title(el.text)
        unknown_index += 1
        return "UNKNOWN_%d" % unknown_index

    if type(xml_stream) == type(''):
        xml_stream = open(xml_stream, 'r', encoding='utf-8')

    event_count = 0
    context = ET.iterparse(xml_stream)
    for event, element in context:
        _, _, tag = element.tag.rpartition('}')
        if tag == 'page':
            page_name = str(title_finder(element))
            # This eliminates redirection pages, but this should be done at a later stage, along with disambiguations
            #if "redirect" not in [el.tag.rpartition('}')[2].lower() for el in list(element)]:
            yield (page_name, ET.tostring(element))
            # See for inspiration: http://www.ibm.com/developerworks/xml/library/x-hiperfparse/
            element.clear()
            #while element.getprevious() is not None:
            #    del element.getparent()[0]
        event_count += 1
    del context

def split_bz2(filename):
    split_xml(gzip.BZ2File(filename, 'r'))

if __name__ == '__main__':
    global args
    import json
    def_config = json.load(open("config.json"))
    parser = argparse.ArgumentParser(description='Expand wikipedia file into page files')
    parser.add_argument('-x', '--xml', help="Indicates that the specified file is an already-unzipped xml file (rather than bz2)", action="store_true")
    parser.add_argument('-o', '--output', help="Changes the output directory", default=def_config['db_directory'])
    #parser.add_argument('-n', '--no_ns', help="Removes the namespace from the xml attribute tags before exporting", default=True, type=bool)
    parser.add_argument('-c', '--commit', help="Set the number of records to be queued before committing to the database", default=10000, type=int)
    parser.add_argument('-v', '--verbose', help="Prints page titles as they get output", action="store_true")
    parser.add_argument('filename', help="The filepath to the wikipedia dump file")
    args = parser.parse_args()

    if(args.xml):
        split_xml(open(args.filename))
    else:
        split_bz2(args.filename)
