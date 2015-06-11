#!/usr/bin/env python3

'''
A runnable script that can guide a user through finding the download links
for wikipedia archive files. Execute from terminal and follow the directions
to find the best links for downloading. Note that this script does not
actually download any files itself, since this process can take long enough
that a proper download manager is recommended to be used. For use with
wikiparse, it is recommended to download
English -> latest -> pages-articles -> single -> xml.bz2

Each menu in the process has the following features:
- Help documentation to instruct you in that particular menu's use. There
is help here if you're not sure what the menu options mean.
- Back, to return to previous menus
- Case-insensitive command completion, as long as your partial input
unambiguously refers to a single command, it will be run

If using wikiparse as an offline Wikipedia module, this is your first step
to obtain the wikitext for all Wikipedia pages. If you don't want to download
the entire archive, individual pages can be obtained on demand, but this may
be much slower for large numbers of pages.

This script has no command-line options.

Below shows a sample run of this script:

::

    Language selection
      English
      Catalan
      Chinese
      French
      German
      Italian
      Japanese
      Polish
      Portugese
      Russian
      Spanish
      Other
      BACK
    > eng
    Date selection
      latest
      20150602
      20150515
      20150403
      20150304
      20150205
      20150204
      20150112
      20141208
      20141106
      BACK
    > latest
    Type selection (use 'pages-articles' for wikiparse toolchain)
      abstract
      all-titles-in-ns
      all-titles
      category
      categorylinks
      externallinks
      flaggedpages
      flaggedrevs
      geo_tags
      image
      imagelinks
      interwiki
      iwlinks
      langlinks
      md5sums
      page
      page_props
      page_restrictions
      pagelinks
      pages-articles-multistream-index
      pages-articles-multistream
      pages-articles
      pages-logging
      pages-meta-current
      pages-meta-history
      protected_titles
      redirect
      site_stats
      stub-articles
      stub-meta-current
      stub-meta-history
      templatelinks
      user_groups
      HELP
      BACK
    > pages-articles
    File selection
      Single file
      Multiple files
      BACK
    > single
    Extension selection
      xml.bz2
      xml.bz2-rss.xml
      BACK
    > xml.bz2
    Download the following links:
    https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2


.. moduleauthor:: David Maxson <jexmax@gmail.com>
'''

from collections import OrderedDict
import urllib.request
from bs4 import BeautifulSoup as BS
import re

DL_BASE = r"https://dumps.wikimedia.org"
DL_LANG = r""
DL_DATE = r""
DL_TYPE = r""

DL_ROOT_URL = lambda: "/".join(st for st in [DL_BASE, DL_LANG, DL_DATE] if len(st) > 0)
DL_FILE_PREFIX = lambda: "".join("%s-" % pref for pref in [DL_LANG, DL_DATE] if len(pref) > 0)
AVAIL_LINKS = None
POTENTIAL_LINKS = None
SKIP_NUMS = None

def unique(list):
    st = set()
    for el in list:
        if el not in st:
            yield el
        st.add(el)

def count(i = 1):
    while True:
        yield i
        i += 1

class Menu(object):
    BACK = 0
    QUIT = 1
    LOOP = 2

    def __init__(self, title, items):
        self.title = title
        self._options = items
        self._options['BACK'] = lambda: True

    def __call__(self, *args, **kwargs):
        return self.handle_loop()

    def handle_loop(self):
        while True:
            print(self.title)
            print("\n".join("  %s" % key for key, val in self._options.items()))
            selection = input("> ")
            possibilities = [(k, v) for k, v in self._options.items() if k.lower() == selection.lower()]
            if len(possibilities) == 0:
                possibilities = [(k, v) for k, v in self._options.items() if k.lower().startswith(selection.lower())]
            if len(possibilities) == 1:
                res = possibilities[0][1]()
                if res == Menu.QUIT:
                    return Menu.QUIT
                if res == Menu.BACK:
                    return Menu.LOOP
                if res == Menu.LOOP:
                    continue
            elif len(possibilities) > 1:
                print("'%s' is an ambiguous choice, did you mean one of the following?" % selection)
                print("\n".join("  %s" % key for key, val in possibilities))
            else:
                print("'%s' does not match any possible options" % selection)

languages = [
    ("English", "en"),
    ("Catalan", "ca"),
    ("Chinese", "zh"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Japanese", "ja"),
    ("Polish", "pl"),
    ("Portugese", "pt"),
    ("Russian", "ru"),
    ("Spanish", "es")
]
class LanguageMenu(Menu):
    def __init__(self):
        langs = OrderedDict([(title, self.pick_language(code)) for title, code in languages])
        langs['Other'] = self.custom_language
        super(LanguageMenu, self).__init__("Language selection", langs)

    def pick_language(self, lang_prefix):
        def inner():
            global DL_LANG
            DL_LANG = "%swiki" % lang_prefix
            return DateMenu()()
        return inner

    def custom_language(self):
        print("Enter 2-character language code:")
        selection = input("> ")
        return self.pick_language(selection.lower())()

class DateMenu(Menu):
    def __init__(self):
        cur_url = DL_ROOT_URL()
        html = urllib.request.urlopen(cur_url).read()
        soup = BS(html)
        links = soup.pre.find_all('a')
        link_names = [res for res in reversed([lnk['href'].partition("/")[0] for lnk in links]) if res != ".."]
        choices = OrderedDict([(name, self.pick_date(name)) for name in link_names])
        super(DateMenu, self).__init__("Date selection", choices)

    def pick_date(self, date):
        def inner():
            global DL_DATE
            DL_DATE = date
            return TypeMenu()()
        return inner

common_types = OrderedDict([
    ("pages-articles", "RECOMMENDED for use with wikiparse toolchain: Current revisions only, no talk or user pages; this is probably what you want, and is approximately 10 GB compressed (expands to over 40 GB when uncompressed)."),
    ("pages-meta-current", "Current revisions only, all pages (including talk)"),
    ("abstract", "Page abstracts"),
    ("all-titles-in-ns", "Article titles only (with redirects)"),
    ("For more information, see", r"https://en.wikipedia.org/wiki/Wikipedia:Database_download")
])

class TypeMenu(Menu):
    def __init__(self):
        global AVAIL_LINKS
        cur_url = DL_ROOT_URL()
        html = urllib.request.urlopen(cur_url).read()
        soup = BS(html)
        if DL_DATE == "latest":
            links = [res for res in (a['href'] for a in soup.find_all('a')) if res != ".."]
        else:
            links = [li.find_all('a')[0]['href'].rpartition("/")[2] for li in soup.find_all('li') if li['class'] == ['file'] and len(li.find_all('a')) > 0]
        AVAIL_LINKS = links
        printable_links = [lnk.partition(DL_FILE_PREFIX())[2 if DL_FILE_PREFIX() in lnk else 0] for lnk in links]
        printable_links = [re.match(r"^([^\.]+?)\d*\.", lnk) for lnk in printable_links]
        printable_links = [mtch.group(1) for mtch in printable_links if mtch is not None]
        printable_links = [el for el in unique(printable_links) if len(el.strip()) > 0]
        types = OrderedDict([(lnk, self.pick_type(lnk)) for lnk in printable_links])
        types["HELP"] = self.help

        super(TypeMenu, self).__init__("Type selection (use 'pages-articles' for wikiparse toolchain)", types)

    def pick_type(self, type):
        def inner():
            global DL_TYPE
            DL_TYPE = type
            return FileMenu()()
        return inner

    def help(self):
        print("\n".join("%s: %s" % help_topic for help_topic in common_types))
        return Menu.LOOP

class FileMenu(Menu):
    def __init__(self):
        global AVAIL_LINKS
        base = DL_FILE_PREFIX() + DL_TYPE
        esc_base = "".join(r"%s%s" % ((r'' if c.isalnum() else '\\'), c) for c in base)
        single_matcher = re.compile(esc_base + r"\.")
        multi_matcher = re.compile(esc_base + r"\d+\.")
        self.single_links = [lnk for lnk in AVAIL_LINKS if single_matcher.match(lnk) is not None]
        self.multi_links = [lnk for lnk in AVAIL_LINKS if multi_matcher.match(lnk) is not None]

        choices = []
        if len(self.single_links) > 0:
            choices.append(("Single file", self.dl_single))
        if len(self.multi_links) > 0:
            choices.append(("Multiple files", self.dl_multi))

        super(FileMenu, self).__init__("File selection", OrderedDict(choices))
        
    def dl_single(self):
        global POTENTIAL_LINKS, SKIP_NUMS
        POTENTIAL_LINKS = self.single_links
        SKIP_NUMS = False
        return ExtensionMenu()()

    def dl_multi(self):
        global POTENTIAL_LINKS, SKIP_NUMS
        POTENTIAL_LINKS = self.multi_links
        SKIP_NUMS = True
        return ExtensionMenu()()

class ExtensionMenu(Menu):
    partial_find = r'xml-p\d+p\d+'
    partial_flag = "xml-PART"

    def __init__(self):
        global POTENTIAL_LINKS, SKIP_NUMS
        exts = [lnk.split(".")[1:] for lnk in POTENTIAL_LINKS]
        exts = [[ExtensionMenu.partial_flag if re.match(ExtensionMenu.partial_find, ext) else ext for ext in lst] for lst in exts]
        exts = [".".join(lst) for lst in exts]
        exts = list(unique(exts))

        super(ExtensionMenu, self).__init__("Extension selection", OrderedDict([(inner_ext, self.pick_ext(SKIP_NUMS, inner_ext)) for inner_ext in exts]))

    def pick_ext(self, skip_nums, ext):
        def inner():
            global POTENTIAL_LINKS
            exts = ext.split(".")
            exts = ["".join("%s%s" % (("\\" if not c.isalnum() else ""), c) for c in inner_ext) if inner_ext.lower() != ExtensionMenu.partial_flag.lower() else ExtensionMenu.partial_find for inner_ext in exts]
            regex = DL_FILE_PREFIX() + DL_TYPE + ("\d+" if skip_nums else "") + "".join(r"\.%s" % inner_ext for inner_ext in exts) + "$"
            matched_files = [lnk for lnk in POTENTIAL_LINKS if re.match(regex, lnk) is not None]
            print("Download the following links:")
            print("\n".join("%s/%s" % (DL_ROOT_URL(), mtch) for mtch in matched_files))
            return Menu.QUIT
        return inner

def run():
    LanguageMenu()()

if __name__ == "__main__":
    run()