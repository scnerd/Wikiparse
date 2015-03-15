#!/usr/bin/env python3

XML = "XML"
SQL = "SQL"
OUTPUT_TYPE = SQL

DB_NAME = "wikipedia.sqlite"

import os, bz2, argparse, sys, re
from xml.etree import ElementTree as ET
import atexit
atexit.register(lambda: print("%s has been closed gently" % __file__))
if OUTPUT_TYPE == SQL:
    import sqlite3 as sql
    def initialize_sql(output_directory):
        path = os.path.join(output_directory, DB_NAME)
        initialize = False
        if not os.path.isfile(path):
            initialize = True
        connection = sql.connect(path)
        atexit.register(connection.close)
        atexit.register(connection.commit)
        if initialize:
            cur = connection.cursor()
            cur.execute(r"CREATE TABLE pages (id INTEGER PRIMARY KEY, title TEXT, xml_bz2 BLOB);")
            connection.commit()
        return connection
else:
    print("Must select valid output type (XML or SQL)")
    exit(1)
from unidecode import unidecode
from queue import Queue
if not OUTPUT_TYPE == SQL:
    from threading import Thread
from time import time

VALID_DIR_CHARS = re.compile("[\w\d]")
def get_sub_directory(title, depth):
    return [c.upper() for c in VALID_DIR_CHARS.findall(title)][:depth]

cleaner = re.compile(r"[^\(\)\-\_\.\s\w\d]|^[^\w\d]")
def normalize_title(title):
    return cleaner.sub("_", unidecode(title).strip())

def output_worker(compress, output_directory, depth):
    file_open = lambda name: bz2.BZ2File(name, 'w') if compress else open(name, 'wb')
    def save_text(path, text):
        try:
            with file_open(path) as output_file:
                output_file.write(text)
            return True
        except (PermissionError, FileNotFoundError):
            return False
        #except MemoryError:
        #    sleep(5)
        #    return save_text(path, text)
    if OUTPUT_TYPE == XML:
        def output_page(title, page):
            output_text = page
            dir = os.path.join(output_directory, *get_sub_directory(title, depth))
            try:
                if not os.path.isdir(dir):
                    os.makedirs(dir)
            except FileExistsError:
                pass
            path_generator = lambda n: os.path.join(dir, title + ("" if n is None else "." + str(n)) + ".xml" + (".bz2" if compress else ""))
            output_path = path_generator(0)
            rnm = 1
            while os.path.isfile(output_path) or not save_text(output_path, output_text):
                output_path = path_generator(rnm)
                rnm += 1
            del output_text
    elif OUTPUT_TYPE == SQL:
        connection = initialize_sql(output_directory)
        num_runs = 0
        to_commit = []
        def dump():
            c = connection.cursor()
            c.executemany("INSERT INTO pages (title, xml_bz2) VALUES (?, ?)", to_commit)
            connection.commit()
            to_commit.clear()
        atexit.register(dump)
        def output_page(title, page):
            nonlocal num_runs
            global args
            to_commit.append((title, bz2.compress(page)))
            num_runs += 1
            if num_runs >= args.commit:
                dump()
                num_runs = 0
    def perform_work():
        while True:
            title, page = output_q.get()
            output_page(title, page)
            output_q.task_done()
            if OUTPUT_TYPE == SQL:
                return
    return perform_work

output_q = Queue(1000)
page_q = Queue(1000)
num_threads = 7
def split_xml(xml_stream, compress, output_directory, depth, verbose):
    if OUTPUT_TYPE != SQL:
        for i in range(num_threads):
            t = Thread(target=output_worker(compress, output_directory, depth))
            t.daemon = True
            t.start()
    else:
        worker = output_worker(compress, output_directory, depth)
    num = 0
    prev_time = 0
    for title, page in find_pages(xml_stream, verbose):
        num += 1
        if verbose:
            print(title)
        else:
            if time() - prev_time >= .1:
                prev_time = time()
                #tr.print_diff()
                #print(num)
                sys.stdout.write("%d\r" % num)
                sys.stdout.flush()
        output_q.put((title, page))
        if OUTPUT_TYPE == SQL:
            worker()
    output_q.join()


def find_pages(xml_stream, verbose):
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

def split_bz2(bz2_filename, *args, **kwargs):
    split_xml(bz2.BZ2File(bz2_filename, 'r'), *args, **kwargs)

global args
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Expand wikipedia file into page files')
    parser.add_argument('-x', '--xml', help="Indicates that the specified file is an already-unzipped xml file (rather than bz2)", action="store_true")
    parser.add_argument('-o', '--output', help="Changes the output directory", default="./wikipedia")
    parser.add_argument('-v', '--verbose', help="Prints page titles as they get output", action="store_true")
    if OUTPUT_TYPE == XML:
        parser.add_argument('-u', '--uncompressed', help="Leaves output files uncompressed", action="store_true")
        parser.add_argument('-d', '--depth', help="Sets the directory branching depth to use under the root output directory", default=3, type=int)
    elif OUTPUT_TYPE == SQL:
        parser.add_argument('-c', '--commit', help="Set the number of records to be queued before committing to the database", default=10000, type=int)
    parser.add_argument('filename', help="The filepath to the wikipedia dump file")
    args = parser.parse_args()

    caller = split_xml if args.xml else split_bz2
    if OUTPUT_TYPE == XML:
        depth = int(args.depth) if args.depth is not None else 3
    caller(args.filename, compress = OUTPUT_TYPE == XML and not args.uncompressed, output_directory = args.output, depth = OUTPUT_TYPE == XML and depth, verbose = args.verbose)
