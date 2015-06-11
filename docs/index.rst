Documentation for Wikiparse
***************************

Wikiparse is a tree-based approach to representing Wikipedia pages using tightly connected nodes to allow for flexible
connections between both visible and invisible information available on a page (such as a link and the page it points
to). Data is cached as raw wikitext and as JSON, both for speed and for flexibility, allowing other libraries to use
the produced JSON instead of the front-end Python module if desired. The tree-based layout of pages and the caching of
parsed data results in Wikiparse being both much faster and much more capable than similar libraries. This opens the
door for using Wikipedia in new ways more easily to further research into Natural Language Processing (NLP) using
Wikipedia as a broad, open-source, and up-to-date corpus.

wikipage
========

.. automodule:: wikiparse.wikipage

WikiPage
--------------

.. autoclass:: wikiparse.wikipage.WikiPage
   :members:

PageElement
--------------

.. autoclass:: wikiparse.wikipage.PageElement
   :members:

Context
--------------

.. autoclass:: wikiparse.wikipage.Context
   :members:

Text
--------------

.. autoclass:: wikiparse.wikipage.Text
   :members:

Link
--------------

.. autoclass:: wikiparse.wikipage.Link
   :members:

InternalLink
--------------

.. autoclass:: wikiparse.wikipage.InternalLink
   :members:

ExternalLink
--------------

.. autoclass:: wikiparse.wikipage.ExternalLink
   :members:

Heading
--------------

.. autoclass:: wikiparse.wikipage.Heading
   :members:

Section
--------------

.. autoclass:: wikiparse.wikipage.Section
   :members:

Image
--------------

.. autoclass:: wikiparse.wikipage.Image
   :members:

Template
--------------

.. autoclass:: wikiparse.wikipage.Template
   :members:

TemplateArg
--------------

.. autoclass:: wikiparse.wikipage.TemplateArg
   :members:

Redirection
--------------

.. autoclass:: wikiparse.wikipage.Redirection
   :members:

RichText
--------------

.. autoclass:: wikiparse.wikipage.RichText
   :members:


Configuration
=============

The installation directory for Wikiparse includes a configuration JSON file, ``config.json``. This file specifies
certain behaviors and default values for various tools in the Wikiparse toolset. Unless needed, it is recommended to
leave these values at their defaults. If any changes need to be made, make them before using (or better yet, before
installing) Wikiparse, as many settings can break the cache system if made after unpacking or live-fetching files.

The file is structured as a single object or dictionary with the following keys:

* ``try_pulls``: Whether or not to live-fetch wikitext when the file isn't already cached.
* ``cache_pulls``: Whether or not to cache files when they get generated.
* ``cache_dir``: The directory in which the cache should live.
* ``page_index``: The file in which to keep the page index. Note that this file doesn't get used for much, but is
  maintained in case later implementations can make use of it. This index file currently only holds details about
  pages that get unpacked by :py:mod:`wikiparse.wikisplitter`.
* ``dir_nesting``: The max depth to tree directories. Each subdirectory is chosen based on an alpha-numeric character
  from a page's name, but excessive nesting only creates more directories than is necessary for efficiency.
* ``fetch_url``: The URL (as a Python formatting string) from which wikitext pages can be obtained. To use this
  library on a Wikimedia-backed site besides Wikipedia, change this setting.
* ``disallowed_file_names``: A dictionary of filenames that aren't allowed for one reason or another (such as being
  reserved by the OS or filesystem), and what such filenames should become instead.
* ``verbose_filemanager``: Whether or not the :py:mod:`wikiparse.filemanager` should report what it's doing. Use only
  for debugging.

wikidownloader
==============

.. automodule:: wikiparse.wikidownloader
   :members:

wikisplitter
============

.. automodule:: wikiparse.wikisplitter
   :members:

filemanager
===========

.. automodule:: wikiparse.filemanager
   :members:
