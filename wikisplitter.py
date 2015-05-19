#!/usr/bin/env python3

DB_NAME = "wikipedia.sqlite"

import gzip, argparse, sys
from xml.etree import ElementTree as ET
import atexit
from time import time
import filemanager

global args

atexit.register(lambda: print("wikisplitter has closed gently"))

def verbose(txt):
    if args.verbose:
        print(txt)

def split_xml(xml_stream):
    verbose("Initializing...")
    num = 0
    prev_time = 0

    filemanager.start_recording_index()
    output_page = filemanager.write_wikitext

    for title, page in find_pages(xml_stream):
        num += 1
        if time() - prev_time >= .1:
            prev_time = time()
            if args.verbose:
                sys.stdout.write("%d - % -79s\r" % (num, title[:79]))
                sys.stdout.flush()
            else:
                sys.stdout.write("%d\r" % num)
                sys.stdout.flush()
        output_page(title, page)
    verbose("\nWriting index...")
    filemanager.finish_recording_index()
    verbose("Done")


def find_pages(xml_stream):
    unknown_index = 0
    def title_finder(page_element):
        nonlocal unknown_index
        for el in list(page_element): # Children of this element
            if el.tag.rpartition('}')[2] == 'title':
                return el.text
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
