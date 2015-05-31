import re
import collections
from . import filemanager
import json
from collections import OrderedDict as odict


class PageElement(object):
    def __init__(self, page, cur_section, json_data, make_fake=False):
        if not make_fake:
            self.el_id = json_data['id']
            self.el_type = json_data['type']
            self.section = cur_section
            self.page = page
            self.page.all_elements[self.el_id] = self
        self._iter_elements = []

    def __iter__(self):
        self._iterator = (el for el in self._iter_elements)
        return self

    def __next__(self):
        return self.__getattribute__(next(self._iterator))

    def get_text(self):
        return RichText(self)

    def __str__(self):
        return str(self.get_text())

class Context(PageElement): # Make iterable
    def __init__(self, page, cur_section, json_data, make_fake=False):
        super(Context, self).__init__(page, cur_section, json_data, make_fake)
        if not make_fake:
            self.label = json_data['label']
            self.children = [construct(page, cur_section, el) for el in json_data['children']] if 'children' in json_data else []
            self._iter_elements = None

    @staticmethod
    def fake(label, children):
        ret = Context(None, None, None, make_fake=True)
        ret.label = label
        ret.children = children
        return ret

    def __iter__(self):
        if self._iter_elements is None:
            return self.children.__iter__()
        else:
            return super(Context, self).__iter__()

    def __getitem__(self, item):
        return self.children[item]

class Text(PageElement):
    property_splitter = re.compile(r'^(.+)\((\d+)\)$')

    def __init__(self, page, cur_section, json_data):
        super(Text, self).__init__(page, cur_section, json_data)
        self.text = str(json_data['text'])
        Prop = collections.namedtuple('Prop', ['id', 'type'])
        self.properties = [str(prop) for prop in json_data['properties']]
        self.properties = [(prop, Text.property_splitter.match(prop)) for prop in self.properties]
        self.properties = [Prop(mtch.groups(1), mtch.groups(0)) if mtch is not None else Prop("ERROR PARSING: %s" % txt, -1) for txt, mtch in self.properties]
        self._iter_elements = ['text']

class Link(Context):
    def __init__(self, page, cur_section, json_data):
        super(Link, self).__init__(page, cur_section, json_data)
        self.target = json_data['target']
        self.default_text = construct(page, cur_section, json_data['default_text'])
        self.text = self.default_text if len(self.children) == 0 else self
        if len(self.children) == 0:
            self._iter_elements = ['default_text']
        else:
            self._iter_elements = []
            for child in self.children:
                label = '_text%d' % self.children.index(child)
                self.__setattr__(label, child)
                self._iter_elements.append(label)

class InternalLink(Link):
    def __init__(self, page, cur_section, json_data):
        super(InternalLink, self).__init__(page, cur_section, json_data)

class ExternalLink(Link):
    def __init__(self, page, cur_section, json_data):
        super(ExternalLink, self).__init__(page, cur_section, json_data)

class Heading(Context):
    def __init__(self, page, cur_section, json_data):
        super(Heading, self).__init__(page, cur_section, json_data)
        self.level = json_data['level']

class Section(Context):
    def __init__(self, page, cur_section, json_data, make_fake=False):
        super(Section, self).__init__(page, cur_section, json_data, make_fake)
        if not make_fake:
            self.level = json_data['level']
            self.title = construct(page, self, json_data['title'])
            self.body = construct(page, self, json_data['body'])
        self._iter_elements = ['body']

    @staticmethod
    def _fake(title=""):
        ret = Section(None, None, None, make_fake=True)
        ret.level = -1
        ret.title = title
        ret.body = []
        return ret

class Image(Context):
    def __init__(self, page, cur_section, json_data):
        super(Image, self).__init__(page, cur_section, json_data)
        self.page = json_data['link_page']
        self.url = json_data['url']
        self.target = json_data['target']
        self.title = construct(page, cur_section, json_data['title'])
        self._iter_elements = [] # Prevents inner text from appearing as plaintext output

class Template(Context):
    def __init__(self, page, cur_section, json_data):
        super(Template, self).__init__(page, cur_section, json_data)
        self.title = construct(page, cur_section, json_data['title'])
        #self._iter_elements = [] # Prevents inner text from appearing as plaintext output

class TemplateArg(Context):
    def __init__(self, page, cur_section, json_data):
        super(TemplateArg, self).__init__(page, cur_section, json_data)
        self.name = construct(page, cur_section, json_data['name'])
        self.value = construct(page, cur_section, json_data['value'])
        #self._iter_elements = [] # Prevents inner text from appearing as plaintext output

class Redirection(Text):
    def __init__(self, page, cur_section, json_data):
        super(Redirection, self).__init__(page, cur_section, json_data)
        self.target = json_data['target']
        self._iter_elements = [] # Prevents inner text from appearing as plaintext output

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

def construct(page, cur_section, json_data): # introduce current section
    p_type = json_data['type']
    if p_type == "pointer":
        return page.all_elements[json_data['target']]
    else:
        try:
            element = type_mapping[p_type](page, cur_section, json_data)
            return element
        except Exception as ex:
            print("ERROR ON ELEMENT %d" % json_data['id'])
            print("\n".join("%s: %s" % (key, str(val)[:80] + ("..." if len(str(val)) > 80 else "")) for key, val in dict(json_data).items()))
            raise ex

#class PageFilteredElement(PageElement):
#    def __init__(self, src, filter):
#

class RichText(object):
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
                    self._flat.append((sub_el, element.properties))
                    self._lens.append(len(sub_el))
                else:
                    self._flatten(sub_el, visited)

    def __getitem__(self, item):
        item = int(item)
        if item < 0:
            item = self._total_len + item
        for i in range(len(self._lens)):
            cur_len = self._lens[i]
            if item < cur_len:
                cur_txt, cur_props = self._flat[i]
                return cur_txt[item], cur_props
            item -= cur_len
        raise IndexError("Index out of bounds")

    def __len__(self):
        return self._total_len

    def __str__(self):
        return "".join(txt for txt,props in self._flat)



class WikiPage(object):
    def __init__(self, title):
        json_data = json.loads(filemanager.read_json(title))
        if json_data is None:
            raise LookupError("The requested page '%s' was not found" % str(title))
        self.title = title

        self.root_section = Section._fake("__ROOT")
        self.no_section = Section._fake("__NONE")

        self.all_elements = {}
        self.root = construct(self, self.root_section, json_data['root'])
        self.refs = construct(self, self.no_section, json_data['refs'])
        self.internals = [construct(self, self.no_section, el) for el in json_data['internal_links']]
        self.externals = [construct(self, self.no_section, el) for el in json_data['external_links']]
        self.sections = [construct(self, self.no_section, el) for el in json_data['sections']]
        self.sections = odict([(str(sec.title).strip(), sec) for sec in self.sections])
        #self.intro = Context.fake("INTRO", [el for el in self.root['__root'] if type(el) is not Section])

    @staticmethod
    def resolve_page(title, follow_redictions=True):
        page = WikiPage(title)
        if follow_redictions:
            while any(type(el) is Redirection for el in page.all_elements.values()):
                redir_to = next(el for el in page.all_elements.values() if type(el) is Redirection)
                page = WikiPage(redir_to.target)
        return page

    def section_tree(self):
        tmp_sections = list(self.sections.values())
        flat = odict()
        tree = odict()
        flat[str(self.root_section.title)] = tree[str(self.root_section.title)] = (self.root_section, odict())
        prev_len = len(tmp_sections) + 1
        while 0 < len(tmp_sections) < prev_len:
            for i in range(len(tmp_sections)):
                prev_len = len(tmp_sections)
                cur_section = tmp_sections[0]
                tmp_sections = tmp_sections[1:]
                parent_title = str(cur_section.section.title)
                title = str(cur_section.title).strip()
                if parent_title in flat:
                    cur = (cur_section, odict())
                    flat[title] = cur
                    flat[parent_title][1][title] = cur
                else:
                    tmp_sections.append(cur_section)
        for remaining_sec in tmp_sections:
            tree[str(remaining_sec.title)] = (remaining_sec, odict())
        return tree