#!/usr/bin/env python3

'''
A runnable script that can efficiently process an entire wikipedia archive
file and extract the wikitext for every contained page into its own file,
which can be retrieved quickly through the filemanager module. If downloading
wikipdeia for offline caching, this is the second step (after downloading) to
make the downloaded archive usable by the wikiparse library.

Wikisplitter needs to be given the path to the archive file. It is recommended
that, if you download anything, you download the single large archive of
Wikipedia rather than the multiple broken archives. The latter has not been
tested, but the former works correctly.

The ``xml`` (``x``) flag allows you to unzip the archive yourself into just its xml
file (recommended approach if you didn't download the single large zip file),
and then this script will skip the unzipping step. By default, the script
assumes that you are giving it the archive file that's still zipped.

The ``update`` (``u``) flag specifies that you are updating the currently
cached files, which allows wikisplitter to overwrite existing files with
newly unpacked pages.

The ``no_redirects`` (``r``) flag skips outputting redirection pages. Note
that redirection pages can already be handled by wikiparse correctly, so unless
you're trying to save space, reduce the number of files output, or only interested
in actual content pages, you may want to not use this flag.

The ``verbose`` (``v``) flag outputs file names as well as numerical progress
indications while unzipping, and also specifies when other major steps are happening
in the unpacking process.

::

    usage: wikisplitter.py [-h] [-x] [-u] [-r] [-v] filename

    Expand wikipedia file into page files

    positional arguments:
      filename              The filepath to the wikipedia dump file

    optional arguments:
      -h, --help            show this help message and exit
      -x, --xml             Indicates that the specified file is an already-
                            unzipped xml file (rather than bz2)
      -u, --update          Forces overwriting of pages that already exist
      -r, --no_redirects    Ignores redirection pages
      -v, --verbose         Prints page titles as they get output


.. moduleauthor:: David Maxson <jexmax@gmail.com>
'''
from wikiparse import filemanager
filemanager.enable_writing()

DB_NAME = "wikipedia.sqlite"

import gzip, argparse
from xml.etree import ElementTree as ET
import atexit
from time import time

# http://stackoverflow.com/questions/279237/import-a-module-from-a-relative-path
import os, sys, inspect
# realpath() will make your script run, even if you symlink it :)
cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

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
    def output_page(ttl, cnt):
        try:
            filemanager.write_wikitext(ttl, cnt, overwrite=args.update)
        except Exception as ex:
            print("Failed to output page: %s\n%s" % (ttl, repr(ex)))


    verbose("Extracting pages into individual files...")
    if not args.verbose:
        try:
            from tqdm import tqdm
            all_pages = tqdm(find_pages(xml_stream))
            has_progress_bar = True
        except ImportError:
            all_pages = find_pages(xml_stream)
            has_progress_bar = False
    else:
        all_pages = find_pages(xml_stream)
    for title, page in all_pages:
        num += 1
        if (args.verbose or not has_progress_bar) and (time() - prev_time >= 0.1):
            prev_time = time()
            if args.verbose:
                sys.stdout.write("%d - % -79s\r" % (num, title[:79]))
                sys.stdout.flush()
            else:
                sys.stdout.write("%d\r" % num)
                sys.stdout.flush()
        output_page(title, page)
    verbose("\nWriting index...")
    #filemanager.finish_recording_index()
    verbose("Done")


def find_pages(xml_stream):
    unknown_index = 0
    def no_ns(tag):
        return tag.rpartition('}')[2].lower()
        
    def find_el_by_tag(element, tag):
        for el in list(element):
            if no_ns(el.tag) == tag:
                return el
        return None
    
    def title_finder(page_element):
        nonlocal unknown_index
        el = find_el_by_tag(page_element, 'title')
        if el is not None:
            return el.text
        unknown_index += 1
        return "UNKNOWN_%d" % unknown_index
    
    def wikitext_finder(page_element):
        revisions = find_el_by_tag(page_element, 'revision')
        if revisions is not None:
            text = find_el_by_tag(revisions, 'text')
            if text is not None:
                return text.text
        return None
        

    if type(xml_stream) == type(''):
        xml_stream = open(xml_stream, 'r', encoding='utf-8')

    event_count = 0
    context = ET.iterparse(xml_stream)
    for event, element in context:
        tag = no_ns(element.tag)
        if tag == 'page':
            page_name = str(title_finder(element))
            # This eliminates redirection pages, but this should be done at a later stage, along with disambiguations
            is_redirect = find_el_by_tag(element, "redirect")
            if not args.no_redirects or not is_redirect:
                wikitext = wikitext_finder(element)
                yield page_name, wikitext
            # See for inspiration: http://www.ibm.com/developerworks/xml/library/x-hiperfparse/
            element.clear()
            #while element.getprevious() is not None:
            #    del element.getparent()[0]
        event_count += 1
    del context

def split_bz2(filename):
    if filename.endswith('.bz2'):
        import bz2 as unzip
    else:
        import gzip as unzip
    split_xml(unzip.open(filename, 'r'))

if __name__ == '__main__':
    global args
    import json
    def_config = json.load(open("config.json"))
    parser = argparse.ArgumentParser(description='Expand wikipedia file into page files')
    parser.add_argument('-x', '--xml', help="Indicates that the specified file is an already-unzipped xml file (rather than bz2)", action="store_true", default=False)
    #parser.add_argument('-o', '--output', help="Changes the output directory", default=def_config['cache_dir'])
    parser.add_argument('-u', '--update', help="Forces overwriting of pages that already exist", action="store_true", default=False)
    parser.add_argument('-r', '--no_redirects', help="Ignores redirection pages", action="store_true", default=False)
    #parser.add_argument('-n', '--no_ns', help="Removes the namespace from the xml attribute tags before exporting", default=True, type=bool)
    #parser.add_argument('-c', '--commit', help="Set the number of records to be queued before committing to the database", default=10000, type=int)
    parser.add_argument('-v', '--verbose', help="Prints page titles as they get output", action="store_true", default=False)
    parser.add_argument('filename', help="The filepath to the wikipedia dump file")
    args = parser.parse_args()

    if(args.xml):
        split_xml(open(args.filename))
    else:
        split_bz2(args.filename)
