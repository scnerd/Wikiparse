import argparse
parser = argparse.ArgumentParser(description="Provides a python3 frontend to the ANTLR-generated wikipedia parser (which must be generated prior to using this script)")

from antlr4 import *
try:
    from WikiparseGrammarLexer import WikiparseGrammarLexer as lexer
    from WikiparseGrammerParser import WikiparseGrammerParser as parser
except ImportError:
    print("The ANTLR grammar hasn't been generated yet. ry: antlr4 -Dlanguage=Python3 WikiparseGrammar.g4")