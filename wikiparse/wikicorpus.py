import nltk

# http://stackoverflow.com/questions/279237/import-a-module-from-a-relative-path
import os, sys, inspect
# realpath() will make your script run, even if you symlink it :)

cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
if cmd_folder not in sys.path:
   sys.path.insert(0, cmd_folder)
from wikiparse import wikipage

class WikiCorpus(object):
   def __init__(self, *page_names):
      self.page_names = page_names
   
   def __iter__(self):
      for name in self.page_names:
         try:
            yield wikipage.WikiPage(name)
         except:
            pass

   def paras(self):
      for page in self:
         for para in (p.strip() for p in str(page.content).split('\n') if len(p.strip()) > 0):
            yield para
            
   def sents(self):
      for para in self.paras():
         yield from nltk.sent_tokenize(para)
         
   def words(self):
      for sent in self.sents():
         yield from nltk.word_tokenize(sent)
