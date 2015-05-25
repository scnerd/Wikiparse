import re
import collections
import filemanager
import json


class PageElement(object):
    def __init__(self, page, json_data):
        self.el_id = json_data['id']
        self.el_type = json_data['type']
        self.page = page
        self.page.all_elements[self.el_id] = self
        self._iter_elements = []

    def __iter__(self):
        _iterator = self._iter_elements.__iter__()
        def inner_next():
            return self.__getattribute__(_iterator.__next__())
        return staticmethod(inner_next)

class Context(PageElement): # Make iterable
    def __init__(self, page, json_data):
        super(Context, self).__init__(page, json_data)
        self.label = json_data['label']
        self.children = [construct(page, el) for el in json_data['children']] if 'children' in json_data else []
        self._iter_elements = None

    def __iter__(self):
        if self._iter_elements is None:
            return self.children.__iter__()
        else:
            return super(Context, self).__iter__()

class ContextPointer(Context): # Should be basically invisible
    def __init__(self, page, json_data):
        super(ContextPointer, self).__init__(page, json_data)
        self.target = json_data['target']

    def __getattribute__(self, item):
        if item == 'target':
            return object.__getattribute__(self, item)
        return self.page.all_elements[self.target].__getattribute__(item)

class Text(PageElement):
    property_splitter = re.compile(r'^(.+)\((\d+)\)$')

    def __init__(self, page, json_data):
        super(Text, self).__init__(page, json_data)
        self.text = str(json_data['text'])
        Prop = collections.namedtuple('Prop', ['id', 'type'])
        self.properties = [str(prop) for prop in json_data['properties']]
        self.properties = [(prop, Text.property_splitter.match(prop)) for prop in self.properties]
        self.properties = [Prop(mtch.groups(1), mtch.groups(0)) if mtch is not None else Prop("ERROR PARSING: %s" % txt, -1) for txt, mtch in self.properties]
        self._iter_elements = ['text']

class Link(Context):
    def __init__(self, page, json_data):
        super(Link, self).__init__(page, json_data)
        self.target = json_data['target']
        self.default_text = construct(page, json_data['default_text'])
        self.text = self.default_text if len(self.children) == 0 else self
        self._iter_elements = ['text']

class InternalLink(Link):
    def __init__(self, page, json_data):
        super(InternalLink, self).__init__(page, json_data)

class ExternalLink(Link):
    def __init__(self, page, json_data):
        super(ExternalLink, self).__init__(page, json_data)

class Heading(Context):
    def __init__(self, page, json_data):
        super(Heading, self).__init__(page, json_data)
        self.level = json_data['level']

class Section(Context):
    def __init__(self, page, json_data):
        super(Section, self).__init__(page, json_data)
        self.level = json_data['level']
        self.title = construct(page, json_data['title'])
        self.body = construct(page, json_data['body'])
        self._iter_elements = ['body']

class Image(Context):
    def __init__(self, page, json_data):
        super(Image, self).__init__(page, json_data)
        self.page = json_data['page']
        self.url = json_data['url']
        self.target = json_data['target']
        self.title = construct(page, json_data['title'])

class Template(Context):
    def __init__(self, page, json_data):
        super(Template, self).__init__(page, json_data)
        self.title = construct(page, json_data['title'])

class TemplateArg(Context):
    def __init__(self, page, json_data):
        super(TemplateArg, self).__init__(page, json_data)
        self.name = construct(page, json_data['name'])
        self.value = construct(page, json_data['value'])

class Redirection(Text):
    def __init__(self, page, json_data):
        super(Redirection, self).__init__(page, json_data)

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
    'pointer': ContextPointer
}

def construct(page, json_data): # introduce current section
    p_type = json_data['type']
    element = type_mapping[p_type](page, json_data)
    return element

#class PageFilteredElement(PageElement):
#    def __init__(self, src, filter):
#

class RichText(object):
    def __init__(self, element):
        self._flat = []
        self._lens = []
        self._total_len = sum(self._lens)
        self._flatten(self.start)
        self.root = element

    def _flatten(self, element, arr):
        for sub_el in element:
            if type(sub_el) == str:
                self._flat.append((sub_el, element.properties))
                self._lens.append(len(sub_el))
            else:
                self._flatten(sub_el, arr)

    def __getitem__(self, item):
        item = int(item)
        for i in range(len(self._lens)):
            cur_len = self._lens[i]
            if item < cur_len:
                cur_txt, cur_props = self._flat[i]
                return cur_txt[item], cur_props
            item -= cur_len

    def __len__(self):
        return self._total_len



class WikiPage(object):
    def __init__(self, title):
        json_data = json.loads(filemanager.read_json(title))
        self.all_elements = {}
        self.root = construct(self, json_data['root'])
        self.refs = construct(self, json_data['refs'])
        self.internals = [construct(self, el) for el in json_data['internal_links']]
        self.externals = [construct(self, el) for el in json_data['external_links']]
        self.sections = [construct(self, el) for el in json_data['sections']]