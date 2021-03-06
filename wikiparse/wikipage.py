"""
The wikipage module exposes the WikiPage class, which is the primary
tool for retrieving and analyzing Wikipedia pages. The method simply
takes a page title and retrieves the page as a WikiPage object

>>> page = wikipage.WikiPage('Python (programming language)')

The resulting object contains all the textual content of the specified
page. Note that to follow redirections, it is recommended that you use
:py:meth:`WikiPage.resolve_page` instead.

WikiPages are structured internally as trees. Each element in the tree
inherits from :py:class:`PageElement`. The most common type of
PageElement is a :py:class:`Context`, essentially a loose collection
of other page elements. Most types derive from Context, adding some
kind of peripheral information on the side. For example, an
:py:class:`InternalLink` is a :py:class:`Context` whose content is the textual
element of the link, but with an added attribute ``target`` that
specifies which Wikipedia page that link points to. This kind of
separation of the text (e.g., "legislation") from the metadata attached
to that text (e.g., a link to "List of United States federal legislation")
allows for a very clean and simple presentation of the plaintext of a
page without any loss of information.

"""

import re
import collections
import json
from collections import OrderedDict as Odict
# http://stackoverflow.com/questions/279237/import-a-module-from-a-relative-path
import os, sys, inspect
# realpath() will make your script run, even if you symlink it :)

cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)
from wikiparse import filemanager



class PageElement(object):
    """ Represents any node in a :py:class:`WikiPage` tree.
    """

    def __init__(self, page, cur_section, parent, json_data, make_fake=False):
        self._section = cur_section
        self._page = page
        self._parent = parent
        self._iter_elements = []
        if not make_fake:
            self._el_id = json_data['id']
            self._el_type = json_data['type']
            self._page.all_elements[self._el_id] = self

    def __iter__(self):
        self._iterator = (el for el in self._iter_elements)
        return self

    def __next__(self):
        return self.__getattribute__(next(self._iterator))

    def get_text(self):
        """ Gets a :py:class:`RichText` object representing this node and all its children as text.
        """
        return RichText(self)

    def part_of(self):
        """ Returns a set including this object's type and all the types of the contexts in which this object exists.
        """
        return set([type(self)]).union([] if self._parent is None else self._parent.part_of())

    def is_part_of(self, target_type):
        """ Checks whether or not this object belongs, at any level, in a node of the specified type.

        :param target_type: The type of node to check against.
        :type target_type: type
        :return: True if any context in which this object lives is of the specified type.
        :rtype: bool
        """
        return type(self) == target_type or self._parent.is_part_of(target_type)

    def __str__(self):
        return str(self.get_text())

    @property
    def section(self):
        """ The most immediate :py:class:`Section` object in which this node lives.
        """
        return self._section

    @property
    def page(self):
        """ The :py:class:`WikiPage` to which this node belongs.
        """
        return self._page

    @property
    def parent(self):
        """ The immediate :py:class:`Context` that contains this node.
        """
        return self._parent


class Context(PageElement):  # Make iterable
    """ An iterable and indexable node that contains other nodes.
    """

    def __init__(self, page, cur_section, parent, json_data, make_fake=False):
        super(Context, self).__init__(page, cur_section, parent, json_data, make_fake)
        if not make_fake:
            self._label = json_data['label']
            self._content = [construct(page, cur_section, self, el) for el in
                             json_data['children']] if 'children' in json_data else []
        self._iter_elements = None

    @staticmethod
    def _fake(label, children):
        ret = Context(None, None, None, None, make_fake=True)
        ret._label = label
        ret._content = children
        return ret

    def __iter__(self):
        if self._iter_elements is None:
            return self._content.__iter__()
        else:
            return super(Context, self).__iter__()

    def __getitem__(self, item):
        return self._content[item]

    @property
    def label(self):
        """ A string that identifies which kind of context this is. Checking the type of this node is preferred, but
        this string is available if desired. Possible prefixes include:

            * *nothing*: Just a context to group other elements
            * ``__link_``: A link, either internal or external
            * ``__heading_``: A header, usually to a section
            * ``__image_``: A context that contains information about an image
            * ``__section_``: A context that is a section division of its own
            * ``__template_``: A template context, which usually contains template arguments
        """
        return self._label

    @property
    def content(self):
        """ The list of elements contained in this context. Note that Context itself is iterable and indexable, which
        is the preferred way to access the context's contents.
        """
        return self._content


Prop = collections.namedtuple('Prop', ['id', 'name'])


class Text(PageElement):
    """ An element representing displayed text, possibly with formatting properties.
    """
    property_splitter = re.compile(r'^(.+)\((\d+)\)$')

    def __init__(self, page, cur_section, parent, json_data):
        super(Text, self).__init__(page, cur_section, parent, json_data)
        self._text = str(json_data['text'])
        self._properties = [str(prop) for prop in json_data['properties']]
        self._properties = [(prop, Text.property_splitter.match(prop)) for prop in self._properties]
        self._properties = [
            Prop(int(mtch.group(2)), mtch.group(1)) if mtch is not None else Prop("ERROR PARSING: %s" % txt, -1) for
            txt, mtch in self._properties]
        self._iter_elements = ['text']

    @property
    def text(self):
        """ The raw text in this object that gets displayed when printing the page.
        """
        return self._text

    @property
    def properties(self):
        """ The list of properties of this text, contained as tuples like (id, 'name'). These are named tuples, so data
        can also be pulled out of them using "properties[*n*].id" and "properties[*n*].name".
        The following properties are possible:

        * Basic formatting

            - ``bold`` - Bolded text.
            - ``italics`` - Italicized text.
            - ``link`` - The title of a link.

        * Definition lists

            - ``defList`` - A definition list.
            - ``term`` - The term being defined in a definition list.
            - ``def`` - The definition of a term in a definition list.

        * Enumerations

            - ``enum`` - An enumeration list.
            - ``enumItem`` - An item in an enumeration list.

        * Itemized lists

            - ``items`` - An itemized list.
            - ``itemsItem`` - An item in an itemized list.

        * Tables

            - ``table`` - Text within a table.
            - ``tableCaption`` - The caption of a table.
            - ``tableCell`` - The body of a table cell.
            - ``tableHeader`` - The header of a table.
            - ``tableRow`` - A row of a table.

        * XML (uncommon and poorly parsed, these probably shouldn't be showing up very often)

            - ``xml`` - And XML element.
            - ``xmlClose`` - The close of an XML element.
            - ``xmlEmpty`` - An XML element with no content.
            - ``xmlOpen`` - The open of an XML element.
            - ``xmlEntRef`` - A tag surrounding external references. *These shouldn't survive, please report with
              wikitext if you encounter one of these*
            - ``xmlCharRef`` - A tag surrounding character references. *These shouldn't survive, please report with
              wikitext if you encounter one of these*

        * Templates

            - ``tempParameter`` - A parameter to a template.
        """
        return self._properties


class Link(Context):
    """ A hyperlink of some sort. Links are never created directly, but provide an identical interface for both
    :py:class:`InternalLink` and :py:class:`ExternalLink`.
    """

    def __init__(self, page, cur_section, parent, json_data):
        super(Link, self).__init__(page, cur_section, parent, json_data)
        self._target = json_data['target']
        self._default_text = construct(page, cur_section, self, json_data['default_text'])
        self._text = self._default_text if len(self._content) == 0 else self
        if len(self._content) == 0:
            self._iter_elements = ['default_text']
        else:
            self._iter_elements = []
            for child in self._content:
                label = '_text%d' % self._content.index(child)
                self.__setattr__(label, child)
                self._iter_elements.append(label)

    @property
    def target(self):
        """ What the link points to. For an :py:class:`InternalLink`, this is a another Wikipedia page. For an
        :py:class:`ExternalLink`, this is a URL.
        """
        return self._target

    @property
    def default_text(self):
        """ What the display text would be for this link if no other text is explicitly defined
        """
        return self._default_text

    @property
    def text(self):
        """ The :py:class:`Context` that contains the actual display text for this links.
        """
        return self._text


class InternalLink(Link):
    """ A :py:class:`Link` to another Wikipedia page.
    """

    def __init__(self, page, cur_section, parent, json_data):
        super(InternalLink, self).__init__(page, cur_section, parent, json_data)


class ExternalLink(Link):
    """ A :py:class:`Link` to a page outside of Wikipedia.
    """

    def __init__(self, page, cur_section, parent, json_data):
        super(ExternalLink, self).__init__(page, cur_section, parent, json_data)


class Heading(Context):
    """ A heading or label in the text.
    """

    def __init__(self, page, cur_section, parent, json_data):
        super(Heading, self).__init__(page, cur_section, parent, json_data)
        self._level = json_data['level']

    @property
    def level(self):
        """ The level of this heading relative to other headings
        """
        return self._level


class Section(Context):
    """ A section or subsection of the page
    """

    def __init__(self, page, cur_section, parent, json_data, make_fake=False):
        super(Section, self).__init__(page, cur_section, parent, json_data, make_fake)
        if not make_fake:
            self._level = json_data['level']
            self._title = construct(page, self, self, json_data['title'])
            self._body = construct(page, self, self, json_data['body'])
            self._content = self._body._content
        # self._iter_elements = ['body']

    @staticmethod
    def _fake(title="", body=[]):
        ret = Section(None, None, None, None, make_fake=True)
        ret._level = -1
        ret._title = title
        ret._body = body
        return ret

    @property
    def level(self):
        """ The level of this section relative to other sections
        """
        return self._level

    @property
    def title(self):
        """ The name of this section
        """
        return self._title

    @property
    def body(self):
        """ The content of this section
        """
        return self._body


class Image(Context):
    """ A region based on an image
    """

    def __init__(self, page, cur_section, parent, json_data):
        super(Image, self).__init__(page, cur_section, parent, json_data)
        self._link_page = json_data['link_page']
        self._url = json_data['url']
        self._target = json_data['target']
        self._title = construct(page, cur_section, self, json_data['title'])
        self._iter_elements = []  # Prevents inner text from appearing as plaintext output

    @property
    def page(self):
        """ The page for this image
        """
        return self._link_page

    @property
    def url(self):
        """ The url for this image
        """
        return self._url

    @property
    def target(self):
        """ The page that this image links to
        """
        return self._target

    @property
    def title(self):
        """ The title of this image
        """
        return self._title


class Template(Context):
    """ A Wikipedia template, often used to define common constructs such as latitude-longitude or quick-info sidebars.
    """

    def __init__(self, page, cur_section, parent, json_data):
        super(Template, self).__init__(page, cur_section, parent, json_data)
        self._title = construct(page, cur_section, self, json_data['title'])
        # self._iter_elements = [] # Prevents inner text from appearing as plaintext output

    @property
    def title(self):
        """ The title of this template
        """
        return self._title


class TemplateArg(Context):
    """ A name-value pair to be interpreted by a template
    """

    def __init__(self, page, cur_section, parent, json_data):
        super(TemplateArg, self).__init__(page, cur_section, parent, json_data)
        self._name = construct(page, cur_section, self, json_data['name'])
        self._value = construct(page, cur_section, self, json_data['value'])
        # self._iter_elements = [] # Prevents inner text from appearing as plaintext output

    @property
    def name(self):
        """ The name of the argument in the template which this argument addresses
        """
        return self._name

    @property
    def value(self):
        """ The value passed to the template
        """
        return self._value


class Redirection(Text):
    """ An element indicating that this Wikipedia page should redirect to another.
    See :py:meth:`WikiPage.resolve_page` for automatically following redirections.
    """

    def __init__(self, page, cur_section, parent, json_data):
        super(Redirection, self).__init__(page, cur_section, parent, json_data)
        self._target = json_data['target']
        self._iter_elements = []  # Prevents inner text from appearing as plaintext output

    @property
    def target(self):
        """ The page to which this page redirects
        """
        return self._target


type_mapping = {
    'context': Context,
    'text': Text,
    'internal_link': InternalLink,
    'external_link': ExternalLink,
    'heading': Heading,
    'section': Section,
    'image': Image,
    'template': Template,
    'template_arg': TemplateArg,
    'redirection': Redirection,
    'pointer': None
}


def construct(page, cur_section, parent, json_data):  # introduce current section
    p_type = json_data['type']
    if p_type == "pointer":
        return page.all_elements[json_data['target']]
    else:
        try:
            element = type_mapping[p_type](page, cur_section, parent, json_data)
            return element
        except Exception as ex:
            print("ERROR ON ELEMENT %d" % json_data['id'])
            print("\n".join("%s: %s" % (key, str(val)[:80] + ("..." if len(str(val)) > 80 else "")) for key, val in
                            dict(json_data).items()))
            raise ex


# class PageFilteredElement(PageElement):
#    def __init__(self, src, filter):
#

class RichText(object):
    """ A flattened representation of the text belonging to a node in a :py:class:`WikiPage` tree. Generate using
    ``my_page_element.get_text()`` on any :py:class:`PageElement` in your page. Converting this object to a string
    (using :py:meth:`str`) returns a raw text form, or you can index this object directly using the exact same
    indexing as you would on the raw string. Each value returned from indexing this object returns a tuple of the
    requested character in the string paired with the object from which that character's text came.
    """

    def __init__(self, element):
        self._flat = []
        self._lens = []
        self._total_len = sum(self._lens)
        self._flatten(element, set())
        self.root = element

    def _flatten(self, element, visited):
        if element not in visited:
            visited.add(element)
            for sub_el in element:
                if type(sub_el) == str:
                    self._flat.append((sub_el, element))
                    self._lens.append(len(sub_el))
                else:
                    self._flatten(sub_el, visited)

    @property
    def groups(self):
        """ The list of strings and their associated objects from which this object is indexed.
        """
        return self._flat

    def __getitem__(self, item):
        item = int(item)
        if item >= self._total_len:
            raise IndexError("Index out of bounds")
        if item < 0:
            item = self._total_len + item
        for i in range(len(self._lens)):
            cur_len = self._lens[i]
            if item < cur_len:
                cur_txt, cur_elem = self._flat[i]
                return cur_txt[item], cur_elem
            item -= cur_len
        raise IndexError("Index out of bounds")

    def __len__(self):
        return self._total_len

    def __str__(self):
        return "".join(txt for txt, elem in self._flat)


class WikiPage(object):
    """Loads the data for and constructs a page object representing a page from Wikipedia.
    This process automatically obtains the wikitext and JSON cached representations of the page.

    :param title: The name of the page to obtain. Titles cannot be corrected before retrieval of the page,
                  so consider using :py:meth:`wikiparse.filemanager.possible_titles` if you want to make sure that you
                  are using a cached page.
    :type title: str
    """

    def __init__(self, title, follow_redirections=True):
        if follow_redirections:
            actual = WikiPage.resolve_page(title, True)
            for attr in ['title', 'root_section', 'no_section', 'all_elements', 'root',
                         'content', 'templates', 'refs', 'internals', 'externals',
                         'sections', 'intro']:
                attr = "_%s" % attr
                setattr(self, attr, getattr(actual, attr))
        else:            
           json_data = json.loads(filemanager.read_json(title))
           if json_data is None:
               raise LookupError("The requested page '%s' was not found" % str(title))
           self._title = title
   
           self._root_section = Section._fake("__ROOT")
           self._no_section = Section._fake("__NONE")
   
           self._all_elements = {}
           self._root = construct(self, self._root_section, None, json_data['root'])
           self._content = self._root[0]
           self._templates = self._root[1:]
           self._refs = construct(self, self._no_section, None, json_data['refs'])
           self._internals = [construct(self, self._no_section, None, el) for el in json_data['internal_links']]
           self._externals = [construct(self, self._no_section, None, el) for el in json_data['external_links']]
           self._sections = [construct(self, self._no_section, None, el) for el in json_data['sections']]
           self._sections = Odict([(str(sec.title).strip(), sec) for sec in self._sections])
   
           self._intro = Context._fake("INTRO", [el for el in self._content if type(el) is not Section])
           self._root_section._body = [el for el in self.all_elements.values() if el.section == self._root_section]
           self._no_section._body = [el for el in self.all_elements.values() if el.section == self._no_section]

    @property
    def redirection(self):
        """ Gets which page this page redirects to, or None if this is not a redirection page.
        """
        if not hasattr(self, '_redir'):
            if any(type(el) is Redirection for el in self.all_elements.values()):
                self._redir = next(el for el in self.all_elements.values() if type(el) is Redirection).target
            else:
                self._redir = None
        return self._redir

    @staticmethod
    def resolve_page(title, follow_redirections=True):
        """ Retrieves the specified page, capable of following redirection pages.

        :param title: The title of the page to construct
        :type title: str
        :param follow_redictions: Whether or not to follow redirection pages automatically
        :type follow_redictions: bool
        """
        page = WikiPage(title, follow_redirections=False)
        if follow_redirections:
            while page.redirection is not None:
                page = WikiPage(page.redirection, follow_redirections=False)
        return page

    @property
    def section_tree(self):
        """ A dictionary tree of the sections in this page. Each key is the title of a section, with its value being a
        tuple of the section's object and an ordered dictionary containing any subsections.
        """
        if not hasattr(self, "__tree"):
            tmp_sections = list(self._sections.values())
            flat = Odict()
            tree = Odict()
            flat[str(self._root_section._title)] = tree[str(self._root_section._title)] = (self._root_section, Odict())
            prev_len = len(tmp_sections) + 1
            while 0 < len(tmp_sections) < prev_len:
                for i in range(len(tmp_sections)):
                    prev_len = len(tmp_sections)
                    cur_section = tmp_sections[0]
                    tmp_sections = tmp_sections[1:]
                    parent_title = str(cur_section.section.title).strip()
                    title = str(cur_section.title).strip()
                    if parent_title in flat:
                        cur = (cur_section, Odict())
                        flat[title] = cur
                        flat[parent_title][1][title] = cur
                    else:
                        tmp_sections.append(cur_section)
            for remaining_sec in tmp_sections:
                tree[str(remaining_sec.title)] = (remaining_sec, Odict())
            self._tree = tree
        return self._tree

    @property
    def title(self):
        """ The title of this page, as was given to construct the page.
        """
        return self._title

    @property
    def content(self):
        """ The entire content of the main body of this page.
        """
        return self._content

    @property
    def intro(self):
        """ A context containing the introductor section of the page.
        """
        return self._intro

    @property
    def templates(self):
        """ A list of the templates on this page.
        """
        return self._templates

    @property
    def refs(self):
        """ A list of the references tagged in the References section of this page.
        """
        return self._refs

    @property
    def internal_links(self):
        """ A list of all the internal links contained in this page.
        """
        return self._internals

    @property
    def external_links(self):
        """ A list of all the external links contained in this page.
        """
        return self._externals

    @property
    def sections(self):
        """ A flat list of all the sections (and subsections etc) contained in this page.
        """
        return self._sections

    @property
    def all_elements(self):
        """ A flat dictionary of every element contained in this page, indexed by ID.
        """
        return self._all_elements
