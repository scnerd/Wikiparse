# Wikiparse

Wikiparse is a tree-based approach to representing Wikipedia pages using tightly connected nodes to allow for flexible
connections between both visible and invisible information available on a page (such as a link and the page it points
to). Data is cached as raw wikitext and as JSON, both for speed and for flexibility, allowing other libraries to use
the produced JSON instead of the front-end Python module if desired. The tree-based layout of pages and the caching of
parsed data results in Wikiparse being both much faster and much more capable than similar libraries. This opens the
door for using Wikipedia in new ways more easily to further research into Natural Language Processing (NLP) using
Wikipedia as a broad, open-source, and up-to-date corpus.

For complete documentation, see: http://wikiparse.readthedocs.org/

For the paper behind this project, see report/Report.pdf (coming soon)

= Dependencies =

* Python 3

    - unidecode
    - py4j
    - beautifulsoup4

* Java

= Installation =

A standard Python setup script is included. This should fully install the module using "python3 setup.py install".
