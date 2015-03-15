# http://www.mediawiki.org/wiki/Markup_spec/ANTLR/draft

grammar mediawiki10;
options { /*tokenVocab=mediawikil;*/ language=Python3 output=AST; memoize=true;}
tokens {
   ARTICLE;
   START;
   INTERNAL_LINK;
   ENTITY;
   RD;
   H1;
   H2;
   H3;
   H4;
   H5;
   H6;
   HR;
   P;
   IMG;
   NBSP;
   PROTOCOL;
   TEXT; // all subnodes should be concatenated
   BALD_URL;
   EXTERNAL_LINK;
   IMG;
   ITALICS;
   BOLD;
   B_ON;
   B_OFF;
   BOLD_ITALICS;
   I_ON;
   I_OFF;
   BR;
   UL;
   OL;
   DL;
   LI;
   DD;
   DT;
   ISBN;
   RFC;
   PMID;
   PRE;
   NBSP160; // a real nbsp, like &#160;
   PAGENAME;
   ANGLE_TAG;

   LT; // generally set by the nowiki rule...
   ESCAPED_PUNC;
   CATEGORY;
   TABLE;
   TR;
   TD;
   TH;
   CAPTION;

   IMG_OPTION;
   IMG_OPTION_THUMBNAIL;
   IMG_OPTION_SIZE;
   IMG_OPTION_MANUALTHUMB;
   IMG_OPTION_THUMB;
   IMG_OPTION_FRAME;
   IMG_OPTION_FRAMELESS;
   IMG_OPTION_UPRIGHT;
   IMG_OPTION_BORDER;
   IMG_OPTION_SIZE;
   IMG_OPTION_LEFT;
   IMG_OPTION_CENTER;
   IMG_OPTION_RIGHT;
   IMG_OPTION_NONE;
   IMG_OPTION_BASELINE;
   IMG_OPTION_SUB;
   IMG_OPTION_SUPER;
   IMG_OPTION_TOP;
   IMG_OPTION_TEXT_TOP;
   IMG_OPTION_MIDDLE;
   IMG_OPTION_BOTTOM;
   IMG_OPTION_TEXT_BOTTOM;

   MAGIC_WORD;

}

@lexer::members {
  boolean in_nowiki = false;
  boolean in_noparse = false;
  boolean in_pre = false;
  boolean in_html = false;
  boolean in_listprefix = false;
}



/* Bugs:
<Nowiki> at start of article

ISBN 123456789xxx shouldn't match but does.
<!-- comments at start of line doesn't seem to work -->


Why do I have to write ((ws)=>ws)? everywhere instead of ws?
grrr.

Supports:
* Internal links
* External links (limited range of characters allowed)
* Images (all options)
* Headings (limits on ='s in the text)
* Nowiki, pre
* French punctuation ( foo ? -> foo&nbsp;?)
* HTML entities (&nbsp; is recognised, &foo; is converted to literals)
* Dangerous HTML, < -> &lt; etc
* Bold, italics (supports the basic rules, not the single-character stuff)
* Paragraphs
* Space-indented blocks
* Lists (intentionally doesn't support nested ; lists, does support ;foo:blah)
* ISBN, RFC, PMID (fully, I think)
* HTML comments
* HTML entities: &nbsp; ...
* Inline HTML (<b>, <div> etc)
* Categories
* Tables
* __TOC__, NOTOC, NOEDITSECTION, NOGALLERY, FORCETOC (all minimally - simply recognises and tags them)

Does not support:
* -{ ... }- auto translation stuff


Other limitations:
* Very reduced ranges of characters for many things, like it doesn't
know that é is a letter rather than punctuation, for instance
* Case sensitivity in some places (<NOWIKI> is not recognised)

*/




@members {
  String _mw_image_namespace = "image";
  String _mw_category_namespace = "category";
  boolean in_header=false;
  boolean prohibit_literal_colon=false;
  boolean text_bold=false;
  boolean text_italics=false;
  boolean literal_whitespace=false;
  // These flags are ints because they nest: value 3 means inside 3 levels of stuff that prohibits that character
  int prohibit_literal_pipe=0;
  int prohibit_literal_link_end=0;
  int prohibit_literal_double_pipe=0;
  int prohibit_literal_double_exclamation=0;
  int prohibit_opening_literal_pipe=0; // in table cells, can't start a line with a literal pipe
  int prohibit_literal_exclamation=0; // in table header cells, can't start a line with an exclamation

//  int prohibit_literal_right_bracket=0;
  // this doesn't nest: external links can't contain external links
  boolean prohibit_literal_right_bracket=false;
  int caption_levels = 0;
  int text_levels =0;

  boolean textis(String mw) {
    return input.LT(1).getText().equalsIgnoreCase(mw);
  }

  boolean is_magic_word() {
    return
        input.LT(1).getText().equalsIgnoreCase("NOTOC") ||
        input.LT(1).getText().equalsIgnoreCase("TOC") ||
        input.LT(1).getText().equalsIgnoreCase("FORCETOC") ||
        input.LT(1).getText().equalsIgnoreCase("NOGALLERY") ||
        input.LT(1).getText().equalsIgnoreCase("NOEDITSECTION")
    ;
  }


}

/*
At the very highest level, a page is either a redirect or an article.
*/
start    : {System.out.println("<html>"); }
    (redirect | article)

{System.out.println("</html>"); }
-> ^(START redirect? article?)

;

//////////////////////////////////////////////////////////////////////

/*
A redirect of the form:
 #REDIRECT [[foo]]
Any trailing text is essentially irrelevant. (I guess it should not be parsed)
*/

redirect:
    REDIRECT ws? internal_link (((ws)=>ws)? ((article)=>article)?)
-> ^(RD internal_link article?);


//////////////////////////////////////////////////////////////////////

/*
Treat an article as a series of connected lines with occasional paragraph separators between them.
*/
article: (NL*) (line NL paragraph_separator)*
-> ^(ARTICLE (line paragraph_separator)* );

paragraph_separator: pn*;
pn:
        NL
        /*close_bold_italics */
        { System.out.println("<br />"); } -> /*close_bold_italics */BR ;

close_bold_italics
@after {text_bold=false; text_italics = false;}
: /*
        {text_bold==true && text_italics==true}? =>  -> B_OFF I_OFF
       |{text_bold==false && text_italics==true}? => -> I_OFF
       |{text_bold==true && text_italics==false}? => -> B_OFF
*/
       ;

/*
Paragraph level organisation. These are decisions made by the first character on the line, one of:
  - header, eg == foo ==
  - list, eg **:foo
  - horizontal line, eg ----
  - space block, eg <space>foo
  - paragraph, anything else
*/

line:
    (table) => table^
    | (headerline) => headerline^
    | (listmarker) => listline^
    | (hrline)     => hrline^
    | (spaceline)  => spaceline^
    | paragraph^ ;


/*nonpipeline:
    (table) => table^
    | (headerline) => headerline^
    | (listmarker) => listline^
    | (hrline)     => hrline^
    | (spaceline)  => spaceline^
    | (nonpipe) => paragraph^
    ;
*/
nonpipe
@init { prohibit_literal_pipe++; }:
formatted_text_elem;
finally { prohibit_literal_pipe--;}

not_pipe_or_exclamation
@init { prohibit_literal_exclamation++; }:
nonpipe;
finally { prohibit_literal_exclamation--;}



/*

{|style
!foo !! style| foo    <- table_header_cells
|-style               <- row_separator
!foo                  <- table_header_cells again
|style|foo || boo     <- table_data_cells with simple_cells
|blah multi
line row              <- multiline_cell
}|
*/

table:
   LEFT_BRACE PIPE ws? table_format? NL
   ws?
   (table_line ws?)*
   /*ws? */PIPE RIGHT_BRACE
-> ^(TABLE ^(ATTR table_format?) table_line*);

table_line:
//   ws? /* left-factored out to allow parsing without real backtracking.
   (
   (PIPE PLUS) => table_caption
   | (PIPE HYPHEN) => table_row_separator
   | (EXCLAMATION) => table_header_cells
   | (PIPE ~RIGHT_BRACE) => table_data_cells
   );

table_caption:
    PIPE PLUS ws? formatted_text? NL
-> ^(CAPTION formatted_text);

table_row_separator:
    PIPE HYPHEN ws? table_format? NL
-> ^(TR ^(ATTR table_format?));



table_header_cells:
// ! a series of !! header || cells !! terminated by an optional multi-
// line header cell.
    (
         EXCLAMATION! ws?
        ((table_simple_header_cell table_col_heading_separator ) => table_simple_header_cell table_col_heading_separator! ws?)*
         ws?
        (table_multiline_header_cell | NL!)
    );


table_col_heading_separator:
   (EXCLAMATION EXCLAMATION) |
   (PIPE PIPE);

table_simple_header_cell
@init { prohibit_literal_double_exclamation++; prohibit_literal_double_pipe++; }:
   ((table_cell_format single_pipe) =>  table_cell_format single_pipe ws?)?
   contents=inline_text
-> ^(TH ^(ATTR table_cell_format?) $contents?)
;
finally { prohibit_literal_double_exclamation--; prohibit_literal_double_pipe--; }

table_multiline_header_cell:
   ((table_cell_format single_pipe) =>  table_cell_format single_pipe ws?)?
   table_multiline_header_cell_contents
-> ^(TH ^(ATTR table_cell_format?) table_multiline_header_cell_contents?);

// | a series of || style|data || cells || terminated by an optional multi-
// line header cell.
table_data_cells:
        {input.LA(2) != RIGHT_BRACE && input.LA(2) != HYPHEN}? =>  // HYPHEN restriction probably redundant now
         PIPE! ws?
        ((table_simple_data_cell table_simple_data_cell_separator ) => table_simple_data_cell table_simple_data_cell_separator ws?)*
        (table_multiline_data_cell | NL!)
	;

// simple cell is a single liner and uses || separator
table_simple_data_cell
@init { prohibit_literal_double_pipe++; }:
   ((table_cell_format single_pipe) =>  table_cell_format single_pipe ws?)?
   contents=inline_text
-> ^(TD ^(ATTR table_cell_format?) $contents?)
;
finally { prohibit_literal_double_pipe--; }

table_simple_data_cell_separator:
   PIPE PIPE
->   ;


table_multiline_data_cell:
   ((table_cell_format single_pipe) =>  table_cell_format single_pipe ws?)?
   table_multiline_data_cell_contents
-> ^(TD ^(ATTR table_cell_format?) table_multiline_data_cell_contents?);


table_multiline_data_cell_contents
@init { prohibit_opening_literal_pipe++; }:
// basically *anything* is allowed in a table cell...
    NL* ((ws? nonpipe) => line NL+)*
-> line*;
finally { prohibit_opening_literal_pipe--; }

table_multiline_header_cell_contents:
// basically *anything* is allowed in a table header cell...
    NL* ((ws? not_pipe_or_exclamation) => line NL+)*
-> line*;



table_cell_format
@init { prohibit_literal_pipe++; }:
//   formatted_text;
// At some stage this needs to be replaced by something more precise. In particular we don't really want to attempt to actually parse wikitext in CSS...
    inline_text;
finally { prohibit_literal_pipe--; }


table_format:
    formatted_text;



////////////////////////// Lists ////////////////////////////////

/*
Lists are nestable collections of these forms:
*Unordered list
#Ordered list
:Indented list (aka definition item)
;Defined item
;Defined item:defininition item

They nest like this:
**## Two layers of unordered and two layers of ordered list.

Mediawiki supports ";" lists anywhere in the nesting, but it's ugly and useless. I restrict it to the innermost nesting.
*/

listline:
        ul_item
       |ol_item
       |dt_item
       |definition_item
       ;

listprefix: (listmarker)+;
listmarker:    HASH | ASTERISK | COLON | SEMICOLON;

ul_item:
        ASTERISK (
        (listmarker) => { System.out.println("\n<ul><li>"); } listline { System.out.println("\n</li></ul>\n"); }    -> ^(UL listline)
       |                { System.out.println("\n<ul><li>"); } ws? inline_text { System.out.println("\n</li></ul>\n"); } -> ^(UL  inline_text)
       |                { System.out.println("\n<ul>"); }             { System.out.println("\n</ul>\n"); } -> ^(UL) );

ol_item:
        HASH (
        (listmarker) => { System.out.println("\n<ol><li>"); } listline        { System.out.println("\n</li></ol>\n"); } -> ^(OL listline)
       |                { System.out.println("\n<ol><li>"); } ws? inline_text { System.out.println("\n</li></ol>\n"); } -> ^(OL inline_text)
       |                { System.out.println("\n<ol>"); }                     { System.out.println("\n</ol>\n"); }      -> ^(OL) );

dt_item:
        COLON (
        (listmarker) => listline    -> ^(DD listline)
       |                ((ws)=>ws)? inline_text -> ^(DD inline_text)
       |                            -> ^(DD) );

definition_item:
    SEMICOLON
    ((ws) => ws)?
    (
        term=definition_term
        (
            (     COLON) => COLON ((ws)=>ws)? def=inline_text  -> ^(DT $term ^(DD $def))  // ;term:def     (:def is not a real DT as it doesn't nest)
            | (NL COLON) => NL dt_item                         -> ^(DT $term dt_item)     // ;term\n:def   (:def can nest)
            |                                                  -> ^(DT $term)             // ;term
        )
        | -> ^(DT) // a plain ;
    );


/* As in:  ;definition term:Definition - it obviously can't contain a colon. */
definition_term
@init {prohibit_literal_colon = true;}:
    inline_text;
finally {prohibit_literal_colon=false;}


/////////////////////////// Space blocks ///////////////////
spaceline
@init {literal_whitespace = true;}
:
    SPACE ((printing_ws)=>printing_ws)? inline_text?
-> ^(PRE printing_ws? inline_text?);
finally {literal_whitespace = false;}


////////////////////////// Headers /////////////////////////////////

headerline:/* {in_header = true;}*/
(     (header6) => header6^
    | (header5) => header5^
    | (header4) => header4^
    | (header3) => header3^
    | (header2) => header2^
    | (header1) => header1^)
/* {in_header = false;}  */
    ;

header6:
{ System.out.println ("<h6>"); }
                              EQUALS EQUALS EQUALS EQUALS EQUALS EQUALS a+=EQUALS* header_simple_text b+=EQUALS*  EQUALS EQUALS EQUALS EQUALS EQUALS EQUALS
{ System.out.println ("\n</h6>"); }
-> ^(H6 $a* header_simple_text $b*);

header5:
{ System.out.println ("<h5>"); }
                                     EQUALS EQUALS EQUALS EQUALS EQUALS a+=EQUALS* header_simple_text b+=EQUALS* EQUALS EQUALS EQUALS EQUALS EQUALS
{ System.out.println ("\n</h5>"); }
-> ^(H5 $a* header_simple_text $b*);

header4:
{ System.out.println ("<h4>"); }
                                            EQUALS EQUALS EQUALS EQUALS a+=EQUALS* header_simple_text b+=EQUALS* EQUALS EQUALS EQUALS EQUALS
{ System.out.println ("\n</h4>"); }
-> ^(H4 $a* header_simple_text $b*);

header3:
{ System.out.println ("<h3>"); }
                                                   EQUALS EQUALS EQUALS a+=EQUALS* header_simple_text b+=EQUALS* EQUALS EQUALS EQUALS
{ System.out.println("\n</h3>"); }
-> ^(H3 $a* header_simple_text $b*);

header2:
{ System.out.println ("<h2>"); }
                                                          EQUALS EQUALS a+=EQUALS* header_simple_text b+=EQUALS* EQUALS EQUALS
{ System.out.println("\n</h2>"); }
-> ^(H2 $a* header_simple_text $b*);

header1: // buggy I think
{ System.out.println ("<h1>"); }
                                                                 EQUALS a+=EQUALS* header_simple_text b+=EQUALS*  EQUALS
{ System.out.println("\n</h1>"); }

-> ^(H1 $a* header_simple_text $b*);

/********************************** Horizontal rule ***********************/

hrline: HYPHEN HYPHEN HYPHEN HYPHEN HYPHEN*
-> ^(HR);

/********************************** Paragraph *****************************/
/* Paragraph is rich marked up text that is not covered under one of the other block categories */
// uncertain whether inline_text should be mandatory. problems with lines that consist only of <!-- comment -->...
paragraph: ((ws)=>ws)?  inline_text?
-> ^(P inline_text);

/********************************** Inline text **************************/
inline_text
/*
The highest level of text formatting, appearing in paragraphs and image captions. All character formatting and inline elements are possible, including:
  - inline images: [[image:foo.jpg]]
  - external links: [http://foo.com]
  - internal links: [[foo]]
  - magic links: ISBN 12345667890x
  - 'pre' blocks (wait, are these just a special case of html tags?)
  - "simple inline elements" - see the next section for those.
*/
@init { text_levels++; }
:
(
    // [[http://foo.com]] has to be treated as: [, [http;//foo.com], ]
    ((LEFT_BRACKET LEFT_BRACKET LEFT_BRACKET) => literal_left_bracket // try and save it some time on [[[foo]]]?
    |(literal_left_bracket bracketed_url) => literal_left_bracket
    |(image)              => image
    |(category)           => category
    |(external_link)      => external_link
    |(internal_link)      => internal_link
    |(magic_link)         => magic_link
    |(magic_word)         => magic_word
    |pre_block
    |(formatted_text_elem) =>formatted_text_elem
    )
    ((nbsp_before_punctuation) => nbsp_before_punctuation)?
    ((ws) =>printing_ws)?
)+;
finally { text_levels --;}



/*
Internal links link to somewhere else in the wiki. The most complicated form is:
[[namespace:path/to/page name|Caption with ''formatting'']]trails

Image and category links look very similar, but are treated separately due to special flags etc.

*/
internal_link:
    link_start COLON? pagename
    { System.out.print("<a href='" + $pagename.text + "'>");}
    // [[foo]] and [[foo|]] are both acceptable.
    // this internal question mark seems to be getting ignored?
    (PIPE internal_link_caption?)?
    {
      try {
         String s = $internal_link_caption.text;
      } catch (NullPointerException e) {
        System.out.print($pagename.text);
      }
    }
    // if letters immediately follow the internal link, they are tacked onto the end of the caption. eg [[horse]]s == [[horse|horses]]
    link_end ((letters)=>internal_link_trail)?
    {
     try {
        System.out.print($internal_link_trail.text);
     } catch (NullPointerException e) {
     }
     System.out.print("</a>");
    }
// Issue: Can't currently distinguish [[foo|]] from [[foo]].
-> ^(INTERNAL_LINK ^(PAGENAME pagename) ^(TEXT internal_link_caption? internal_link_trail?));


/* Caption for an internal link is just "simple_text", minus ]]'s.
// Strangely enough, a literal pipe is allowed: [[foo|bar|wa]]
// It would be good if this behaviour were proscribed to allow for future options
*/
internal_link_caption
@init {prohibit_literal_link_end++;}:
        formatted_text;
finally {prohibit_literal_link_end--;}

internal_link_trail: letters; // need to check this, maybe digits ok too? what's the full range?

///////////////////////////////////// Categories /////////////////////////////////////////////////

category: (link_start category_namespace) =>
link_start category_namespace COLON ws? categoryname ( PIPE categorysortkey )? link_end
-> ^(CATEGORY ^(TEXT category_namespace COLON ^(PAGENAME categoryname)) categorysortkey?);

category_namespace        : {textis(_mw_category_namespace)}? mwletters;

categoryname: pagename;

categorysortkey: unformatted_characters;

//////////////////////////////////// Images ///////////////////////////////////////////
/*
Images: option-heavy beasts like [[image:foo.jpg|thumb|100px|Here's a caption...]]
Complications: There's no real way to distinguish a caption from an option. Captions can contain virtually anything, including other images...

Todo:
  - clarify whether /image/paths are ok?
  - clarify whether image names really are just page names...?

*/
image: (link_start image_namespace) =>
link_start image_namespace COLON ws? imagename (  PIPE optionorcaption )* link_end
-> ^(IMG ^(TEXT image_namespace COLON ^(PAGENAME imagename)) optionorcaption*);

image_namespace        : {textis(_mw_image_namespace)}? mwletters;

 imagename
 @init {prohibit_literal_right_bracket=true; prohibit_literal_pipe++;}:
        image_filename_elem
              ((image_filename_elem) => image_filename_elem
               |(SPACE) => SPACE
              )*
        ws? DOT ws? imageextension
//-> ^(PAGENAME pagename DOT imageextension)
;
finally { prohibit_literal_right_bracket=false; prohibit_literal_pipe--;}

image_filename_elem: (letters | digits | accidental_magic_link | UNKNOWN); //| punctuation/* | DIGITS | DOT | UNDERSCORE | HYPHEN | OPEN_PAREN | CLOSE_PAREN*/);


/* Future passes/actions etc can readily retrieve the extension text, so just validate for now? */
 imageextension:
     {textis("jpeg")
     | textis("jpg")
     | textis("png")
     | textis("svg")
     | textis("gif")
     | textis("bmp")}? letters;


optionorcaption
     :    (mw_img_thumbnail (PIPE | link_end)) => mw_img_thumbnail /* move it up here as it's so common */
     |    (SPACE | punctuation) => image_caption
     |    (imageoption (PIPE | link_end)) => imageoption
     |     image_caption;

image_caption
@init {caption_levels++; prohibit_literal_link_end++; prohibit_literal_pipe++;}
: inline_text?
-> ^(TEXT inline_text);
finally {caption_levels--; prohibit_literal_link_end--; prohibit_literal_pipe--;}


mw_img_manualthumb    : {textis("thumbnail") | textis("thumb")}? mwletters EQUALS imagename -> ^(IMG_OPTION_THUMBNAIL imagename);
imageoption:
    mw_img_manualthumb          -> ^(IMG_OPTION_MANUALTHUMB mw_img_manualthumb)
    | mw_img_thumbnail          -> ^(IMG_OPTION_THUMB mw_img_thumbnail)
    | mw_img_frame              -> ^(IMG_OPTION_FRAME mw_img_frame)
    | mw_img_frameless          -> ^(IMG_OPTION_FRAMELESS mw_img_frameless)
    //| mw_img_page weirdly doesn't work, but why?
    | mw_img_upright            -> ^(IMG_OPTION_UPRIGHT mw_img_upright)
    | mw_img_border             -> ^(IMG_OPTION_BORDER mw_img_border)
    | positive_int mw_img_width -> ^(IMG_OPTION_SIZE positive_int)
    | mw_img_left               -> ^(IMG_OPTION_LEFT mw_img_left)
    | mw_img_center             -> ^(IMG_OPTION_CENTER mw_img_center)
    | mw_img_right              -> ^(IMG_OPTION_RIGHT mw_img_right)
    | mw_img_none               -> ^(IMG_OPTION_NONE mw_img_none)
    | mw_img_baseline           -> ^(IMG_OPTION_BASELINE mw_img_baseline)
    | mw_img_sub                -> ^(IMG_OPTION_SUB mw_img_sub)
    | mw_img_super              -> ^(IMG_OPTION_SUPER mw_img_super)
    | mw_img_top                -> ^(IMG_OPTION_TOP mw_img_top)
    | mw_img_text_top           -> ^(IMG_OPTION_TEXT_TOP mw_img_text_top)
    | mw_img_middle             -> ^(IMG_OPTION_MIDDLE mw_img_middle)
    | mw_img_bottom             -> ^(IMG_OPTION_BOTTOM mw_img_bottom)
    | mw_img_text_bottom        -> ^(IMG_OPTION_TEXT_BOTTOM mw_img_text_bottom);

/* default settings: */
/* Hmm, user-definable grammar seems to be a bad idea. Assume that the img_manualthumb is always something followed by the name. */
  mw_img_thumbnail      : {textis("thumbnail") | textis("thumb")}? mwletters -> ^(IMG_OPTION_THUMBNAIL);
 mw_img_frame          : {textis("framed") | textis("enframed") | textis("frame")}? mwletters; //'framed' | 'enframed' | 'frame';
 mw_img_frameless      : {textis("frameless")}? mwletters;
 mw_img_page           : {textis("page")}? mwletters (SPACE | EQUALS) mwletters; //'page=$1' | 'page $1' ; /*??? (where is this used?);*/
 mw_img_upright        : {textis("upright")}? mwletters EQUALS? positive_int?; //'upright' (  '='? POSITIVE_INT)?;
 mw_img_border         : {textis("border")}? mwletters;
 mw_img_width          : {textis("px")}? mwletters;

 mw_img_baseline       : {textis("baseline")}? mwletters;
 mw_img_sub            : {textis("sub")}? mwletters;
 mw_img_super          : {textis("super") | textis("sup")}? mwletters;
 mw_img_top            : {textis("top")}? mwletters;
 mw_img_text_top       : {textis("text-top")}? mwletters;
 mw_img_middle         : {textis("middle")}? mwletters;
 mw_img_bottom         : {textis("bottom")}? mwletters;
 mw_img_text_bottom    : {textis("text-bottom")}? mwletters;

mw_img_left            : {textis("left")}? mwletters;
mw_img_center          : {textis("center") | textis("centre")}? mwletters;
mw_img_right           : {textis("right")}? mwletters;
mw_img_none            : {textis("none")}? mwletters;




/*
External links link to other sites in one of three forms:
  - http://foo.com - bald
  - [http://foo.com] - explicit
  - [http://fooc.com Explicit with caption]
*/
external_link:
        url -> ^(EXTERNAL_LINK ^(TEXT url) ^(TEXT url)) //attempt to use url as caption
        | bracketed_url -> ^(EXTERNAL_LINK bracketed_url);

bracketed_url:    LEFT_BRACKET url (ws external_link_caption)? RIGHT_BRACKET -> ^(TEXT url) ^(TEXT external_link_caption?);

/* badly underspec'ed so far */
url:
    protocol COLON SLASH SLASH domain_elem+ DOT domain_elem+  //    http://foo.com (minimum)
    ((DOT domain_elem+)=>DOT domain_elem+)*                   //    .lom.wom ...
    (SLASH ((urlpath_elem) => urlpath_elem)*)?                                    //    /foo?blah@33!boo.html
    ;

domain_elem:
    letters | digits | HYPHEN;

urlpath_elem:
    letters | digits | HYPHEN | UNDERSCORE | PERCENT | SLASH | DOT | QUESTION | HASH | PLUS | AMP | TILDE | EQUALS | AT | EXCLAMATION | COLON;

protocol: {textis("ftp") | textis("http")}? letters;

external_link_caption
@init {prohibit_literal_right_bracket=true;}
:
    formatted_text;
finally {prohibit_literal_right_bracket=false;}


/*
  Magic links don't require any special punctuation:
    - ISBN 1234567890x
    - RFC 1234
    - PMID 1234
*/

magic_link: isbn_link | pmid_link | rfc_link;
accidental_magic_link: isbn_accidental | pmid_accidental | rfc_accidental;

isbn_link: ISBN_LINK          -> ^(ISBN ISBN_LINK);
isbn_accidental: ISBN_LINK    -> ^(TEXT ISBN_LINK); // the TEXT node is possibly superfluous?

rfc_link: RFC_LINK            -> ^(RFC RFC_LINK);
rfc_accidental: RFC_LINK      -> ^(TEXT RFC_LINK);

pmid_link: PMID_LINK          -> ^(PMID PMID_LINK);
pmid_accidental: PMID_LINK    -> ^(TEXT PMID_LINK);
/////////////////////////////////////////////////////////////////////////

magic_word: UNDERSCORE UNDERSCORE  magic_word_text UNDERSCORE UNDERSCORE
-> ^(MAGIC_WORD magic_word_text);

magic_word_text: {is_magic_word()}? letters;
//magic_word_text: {textis("TOC")}? letters;

////////////////////////////////////////////////////////////////////////

pre_block:
    PRE_OPEN pre_block_body PRE_CLOSE
-> ^(PRE pre_block_body);

pre_block_body:
    (unformatted_characters|pre_ws|NL)*;



/*************** Formatted text *************************/
/*
simple text is basically character formatting. It's used notably:
  - in link captions:  [[The Blah|The ''Blah'']]
  - in external link captions: [http://foo.com '''foo''']
*/
formatted_text
@init { text_levels++; } :
(
    (formatted_text_elem) => formatted_text_elem
    ((nbsp_before_punctuation) => nbsp_before_punctuation)*
    ((printing_ws) => printing_ws)?
)+;
finally { text_levels --; }

formatted_text_elem:
    (
      (accidental_magic_link) => accidental_magic_link
    | ((punctuation_before_nbsp)=> punctuation_before_nbsp)
    | (APOSTROPHES) => bold_and_italics
    |  angle_tag
    | ((html_entity) => html_entity)
    | unformatted_characters
    );

/*
The lowest level: mere text with no formatting. & and < characters are allowed, but are generally converted.
*/
unformatted_characters:
    (html_dangerous
    |punctuation { System.out.print($text); }//* if punctuation+, risk of swallowing too many characters: [[[foo.jpg]]] needs to swallow just one */
    |meaningless_characters { System.out.print($text); }
    |digits { System.out.print($text); }
    );


/*textline: simple_text -> ^(P simple_text);*/

///////////////////////////////////////////////////////////////////////////
bold_and_italics:
     {textis("''") && text_italics}? => APOSTROPHES  {text_italics=false; System.out.print("</i>"); } ->            ^(I_OFF)
    |{textis("''") && !text_italics}? => APOSTROPHES {text_italics=true; System.out.print("<i>"); }   ->            ^(I_ON)
    |{textis("'''") && text_bold}? => APOSTROPHES    {text_bold=false; System.out.print("</b>"); }    ->            ^(B_OFF)
    |{textis("'''") && !text_bold}? => APOSTROPHES   {text_bold=true; System.out.print("<b>"); }      ->            ^(B_ON)
    |{textis("''''") && text_bold}? => APOSTROPHES   {text_bold=false; System.out.print("'</b>"); }   -> APOSTROPHE ^(B_OFF)
    |{textis("''''") && !text_bold}? => APOSTROPHES  {text_bold=true; System.out.print("'<b>"); }     -> APOSTROPHE ^(B_ON)
    |{textis("'''''") && text_bold && text_italics}? =>  APOSTROPHES {text_bold=false; text_italics=false; System.out.print("'</b> </i>");} -> ^(B_OFF) ^(I_OFF)
    |{textis("'''''") && text_bold && !text_italics}? => APOSTROPHES {text_bold=false; text_italics=true; System.out.print("'</b> <i>");}   -> ^(B_OFF) ^(I_ON)
    |{textis("'''''") && !text_bold && text_italics}? => APOSTROPHES {text_bold=true; text_italics=false; System.out.print("'<b> </i>"); }  -> ^(B_ON)  ^(I_OFF)
    |{textis("'''''") && !text_bold && !text_italics}? =>APOSTROPHES {text_bold=true; text_italics=true; System.out.print("'<b> <i>");}     -> ^(B_ON)  ^(I_ON)
    // Hopefully we never get more than 6 or less than 2. The lexer should take care of that.
    ;
////////////////////////Nbsp punctuation/////////////////////////////////
nbsp_before_punctuation:

    SPACE (R_GUILLEMET          { System.out.print("&nbsp; »"); } ->  NBSP160 R_GUILLEMET
          | QUESTION            { System.out.print("&nbsp; ?"); } -> NBSP160 QUESTION
          | COLON               { System.out.print("&nbsp; :"); } -> NBSP160 COLON
          | SEMICOLON           { System.out.print("&nbsp; ;"); } -> NBSP160 SEMICOLON
          | literal_exclamation { System.out.print("&nbsp; !"); } -> NBSP160 EXCLAMATION
          | PERCENT             { System.out.print("&nbsp; \%"); }-> NBSP160 PERCENT
          ) ;


punctuation_before_nbsp:
    L_GUILLEMET SPACE
{ System.out.print("« &nbsp;"); }
    -> L_GUILLEMET NBSP160;

//«»

html_entity:
    AMP (
        html_entity_name SEMICOLON  { System.out.print("&" + $html_entity_name.text + ";"); }        -> ^(ENTITY html_entity_name)
// this line removed as it was causing a crash
//        |  HASH digits SEMICOLON      { System.out.print("&#" + $digits.text + ";"); }         -> ^(ENTITY digits)
//        | '#x' hex_digits SEMICOLON
        )
        ;

// ### To be expanded with help from sanitizer.php
html_entity_name:
        {textis("nbsp")}? => letters;

/*html_open_tag:
        LT html_tag_name        */


//////// //////////////////////////////////////////////////////////////////
pagename
@init {prohibit_literal_right_bracket=true; prohibit_literal_pipe++;}:
        pagename_elem
              ((pagename_elem) => pagename_elem
               | COLON
               | SLASH // will need something a bit more sophisticated
//               | punctuation
               |(SPACE) => SPACE
              )*;
finally { prohibit_literal_right_bracket=false; prohibit_literal_pipe--;}

pagename_elem: (letters | digits | accidental_magic_link | UNKNOWN | punctuation/* | DIGITS | DOT | UNDERSCORE | HYPHEN | OPEN_PAREN | CLOSE_PAREN*/);




/////////////////////////////////// Very basic types ///////////////////////////////////////

/* Currently doesn't support equals during a header title...*/
header_simple_text
@init {in_header=true;}:
        inline_text; /* Pretty much everything seems to be tolerated in headings. (!) */
finally {in_header=false;}

// any need for accidental_magic_link?
mwletters:    letters (letters | HYPHEN | UNDERSCORE | (digits)=>positive_int)*;

/////////////////////////////////// Semi-literals, literal sets etc ///////////////////////////

single_pipe:
   {input.LA(2) != PIPE}? => PIPE;


punctuation :
    DOT |COMMA|OPEN_PAREN | CLOSE_PAREN | HYPHEN
    | HASH | ASTERISK | SEMICOLON | literal_colon
    | UNDERSCORE | SLASH | APOSTROPHE
    | literal_left_bracket
    | literal_right_bracket
    | literal_pipe | literal_equals
    | literal_exclamation
    | L_GUILLEMET | R_GUILLEMET | QUESTION | PERCENT | PLUS | AT | TILDE
    | LEFT_BRACE | RIGHT_BRACE // unconfirmed
    | ESCAPED_PUNC;

html_dangerous:
        LT { System.out.print("&lt;"); } -> ^(ENTITY LT)
      | GT { System.out.print("&gt;"); } -> ^(ENTITY GT)
      | AMP { System.out.print("&amp;"); } -> ^(ENTITY AMP);

angle_tag: ANGLE_TAG { System.out.print($text);}/* -> ANGLE_TAG */;

meaningless_characters:
    (LETTERS | UNKNOWN)+;

letters: (LETTERS);
positive_int: digits; /* needs to be refined to remove 0s at start */
literal_link_end:          {prohibit_literal_link_end <= 0}? => link_end;


literal_right_bracket:
/*@init {
         System.out.println("Entering LRB");
}:     */
//         { !prohibit_literal_right_bracket && (prohibit_literal_link_end <= 0 || input.LA(2)!= RIGHT_BRACKET) }?
//        { !prohibit_literal_right_bracket && (prohibit_literal_link_end <= 0 || input.LA(2)!= RIGHT_BRACKET)  }? => '&';
// weird: if the semantic predicate returns true, everything is ok. if it returns false, an exception is raised.
         //{ false }? => RIGHT_BRACKET;
{ !prohibit_literal_right_bracket && (prohibit_literal_link_end <= 0 || input.LA(2)!= RIGHT_BRACKET) }? =>
    RIGHT_BRACKET;

literal_pipe:
{ !(   prohibit_literal_pipe > 0 ||   (prohibit_literal_double_pipe > 0 && input.LA(2) == PIPE))  }? => PIPE;
  //  || (prohibit_opening_literal_pipe > 0 && getCharPositionInLine()==0) // not correct, need to deal with opening spaces too

/* Three ways of getting a literal right bracket:
1) You're neither in an external nor internal link: foo]
2) You're in an internal link, and not followed by another right bracket:  [[Boop|here] see?]]
3) You're in a nowiki block: [http://square.bracket.com The <nowiki>]</nowiki> foundation.]
*/
//      => RIGHT_BRACKET;
/*finally {
         System.out.println("Exiting LRB");
}*/


/* Dodgy - doesn't really know whether it's a literal left bracket or not */
literal_left_bracket:      LEFT_BRACKET;

/* ;foo:blah is special. ;foo[blah|bl:ah] is not special. TODO: make sure this doesn't break namespaces in defs */
literal_colon:             {!prohibit_literal_colon || text_levels > 1}? => COLON;

// Only supports a single =. So no ==foo==blah==. Currently =<nowiki>=</nowiki>blah== etc doesn't work either.
literal_equals:
    {!in_header || input.LA(2) != EQUALS}? => EQUALS
;

literal_exclamation:
{!(prohibit_literal_exclamation > 0 || prohibit_literal_double_exclamation > 0 && input.LA(2) == EXCLAMATION)}? => EXCLAMATION;


link_start: LEFT_BRACKET LEFT_BRACKET;
link_end: RIGHT_BRACKET RIGHT_BRACKET;

// TODO: apparently image captions always treat spaces literally...
printing_ws:
    {literal_whitespace && text_levels <= 1}? => (pre_ws) => pre_ws
    | ws -> SPACE;

digits:    digit+;
digit: DIGIT;


// Handling of spaces is a bit unclear atm.
ws: ((ws_elem)=>ws_elem)+ { System.out.print(" "); };

pre_ws: ((ws_elem)=>ws_elem)+;
ws_elem:
      SPACE        -> SPACE
    | NOWIKI       ->
    | NOWIKI_OFF   ->
    ;
//    | HTML_COMMENT -> ; // in current mediawiki, comments are stripped out

// apparently identical to previous entry?
/*ws: (SPACE
    | NOWIKI!
    | NOWIKI_OFF!)+ ;*/






///////////////////////////////////////////////////////////////////////////////


REDIRECT:     {getCharPositionInLine()==0 && getLine()==1}? => '#REDIRECT';


//-----------------------------------------------------
/* ISBN magic links. Care will be needed to make sure they're treated as literals wherever they aren't supported. */
// Broken example: [http://ISBN 1234567890] - current parser does correctly. But does it matter?
ISBN_LINK: {!in_noparse}? =>
  // Parser.php l081, ~DIGIT is actually regexp \b
  ((ISBN_LINK_ACTUAL ~DIGIT) => ISBN_LINK_ACTUAL
//  | LETTER { $type=LETTERS; }
  );

fragment
ISBN_LINK_ACTUAL:
    'ISBN'
    ' '+
    ('97' ('8' | '9') (' ' | '-')?)?
    ('0'..'9')
    ((' ' | '-')? '0'..'9')
    ((' ' | '-')? '0'..'9')
    ((' ' | '-')? '0'..'9')
    ((' ' | '-')? '0'..'9')
    ((' ' | '-')? '0'..'9')
    ((' ' | '-')? '0'..'9')
    ((' ' | '-')? '0'..'9')
    ((' ' | '-')? '0'..'9')
    ((' ' | '-')? ('0'..'9' | 'X' | 'x'));


RFC_LINK: {!in_noparse}?=>
  ((RFC_LINK_ACTUAL) => RFC_LINK_ACTUAL
//  | LETTER { $type=LETTER; }
  );

fragment
RFC_LINK_ACTUAL:
    'RFC'
    ' '+
    ('0'..'9')+;



PMID_LINK : {!in_noparse}? =>
  ((PMID_LINK_ACTUAL) => PMID_LINK_ACTUAL
//  | LETTER { $type=LETTERS; }
  );

fragment
PMID_LINK_ACTUAL:
    'PMID'
    ' '+
    ('0'..'9')+;

///////////// <nowiki> / </nowiki>

NOWIKI:
    ({!in_noparse}? => (NOWIKI_ACTUAL) => NOWIKI_ACTUAL { in_nowiki=true; in_noparse=true;}
    |(HTML_COMMENT) => HTML_COMMENT { $type=HTML_COMMENT; $channel=HIDDEN;}
    | '<' { $type=LT; }
    );

fragment
NOWIKI_ACTUAL: '<nowiki>' ;

NOWIKI_OFF: {in_nowiki}? =>
    ((NOWIKI_OFF_ACTUAL) => NOWIKI_OFF_ACTUAL { in_nowiki=false; in_noparse=false;}
    | '<' { $type=LT; }
    );

fragment
NOWIKI_OFF_ACTUAL: '</nowiki>' ;

fragment
HTML_COMMENT: '<!--' .* '-->';


/////////// <pre> / </pre>

PRE_OPEN: {!in_noparse}? =>
    ((PRE_OPEN_ACTUAL) => PRE_OPEN_ACTUAL { in_pre=true; in_noparse=true;}
    | '<' { $type=LT; }
    );

fragment
PRE_OPEN_ACTUAL: '<pre>' ;

PRE_CLOSE: {in_pre}? =>
    ((PRE_CLOSE_ACTUAL) => PRE_CLOSE_ACTUAL { in_pre=false; in_noparse=false; }
    | '<' { $type=LT; }
    );

fragment
PRE_CLOSE_ACTUAL: '</pre>' ;

ANGLE_TAG: { !in_noparse}? =>
    ((ANGLE_TAG_OPEN_ACTUAL) => ANGLE_TAG_OPEN_ACTUAL
    |(ANGLE_TAG_CLOSE_ACTUAL) => ANGLE_TAG_CLOSE_ACTUAL
    | '<' { $type=LT; }
    );

fragment
ANGLE_TAG_OPEN_ACTUAL:   HTML_OPEN | REF_OPEN; // or REF or whatever...

fragment
ANGLE_TAG_CLOSE_ACTUAL:   HTML_CLOSE | REF_CLOSE; // or REF or whatever...
fragment

WS : SPACE+; // should include line feeds later

/* This section from Terrence Parr's HTML grammar */
fragment
ATTR
	:	WORD ('=' (WORD ('%')? | ('-')? INT | STRING | HEXNUM))?
	;
//don't need uppercase for case-insen.
//the '.' is for words like "image.gif"
fragment
WORD:	(	LETTER  | '.' | SLASH )
	(	LETTER  | DIGIT | '.' )+
	;

fragment
STRING	: '"'  (~'"')* '"'
        | '\'' (~'\'')* '\''
	;

fragment
WSCHARS : ' ' | '\t' | '\n' | '\r';


fragment
HEXNUM : HASH HEXINT;

fragment
INT: (DIGIT)+;

fragment
HEXINT
	:	(HEXDIGIT)+
	;

fragment
HEXDIGIT: '0'..'9' | 'a'..'f';

/******************************************************/


/* should be in the tokens section - why didn't that work? */
R_GUILLEMET: '»';
L_GUILLEMET: '«';
QUESTION:    '?';
EXCLAMATION: '!';
PERCENT:     '%';



/* The three 'dangerous' HTML characters */
//LT:                   '<';
GT:                   '>';
AMP:                  '&';


/* It's a literal apostrophe if either the next character is *not* an apostrophe, or the next 5 characters *are* apostrophes. Yummy. */
APOSTROPHE      :  {
      input.LA(1)=='\'' && (
          in_noparse || (
              input.LA(2)!='\'' ||
              input.LA(3)=='\'' &&
              input.LA(4)=='\'' &&
              input.LA(5)=='\'' &&
              input.LA(6)=='\''
          )
      )
}? => APOS;

/* It's a swarm of meaningful apostrophes if it is not the case that this and the next five characters are apostrophes, and there are at least two, and we're not in a nowiki.*/
APOSTROPHES     : {
        !in_noparse &&
        input.LA(1)=='\'' && !(
             input.LA(2)=='\'' &&
             input.LA(3)=='\'' &&
             input.LA(4)=='\'' &&
             input.LA(5)=='\'' &&
             input.LA(6)=='\''
        )
}? => APOS APOS+ ;

fragment
APOS            : '\'';

HASH            : {!in_noparse}? => '#';// {if (in_noparse) $type=ESCAPED_PUNC;};
ASTERISK        : {!in_noparse}? => '*';// {if (in_noparse) $type=ESCAPED_PUNC;};
COLON           : {!in_noparse}? => ':';// {if (in_noparse) $type=ESCAPED_PUNC;};
SEMICOLON       : {!in_noparse}? => ';';// {if (in_noparse) $type=ESCAPED_PUNC;};
PIPE            : {!in_noparse}? => '|';// {if (in_noparse) $type=ESCAPED_PUNC;};
//LEFT_BRACKET    : {!in_noparse}? => '[' {if (in_noparse) $type=ESCAPED_PUNC;};

LEFT_BRACKET    : {!in_noparse}? => '[';
RIGHT_BRACKET   : {!in_noparse}? => ']';
EQUALS          : {!in_noparse}? => '=';// {if (in_noparse) $type=ESCAPED_PUNC;};
SLASH           : {!in_noparse}? => '/';// {if (in_noparse) $type=ESCAPED_PUNC;}; // this is almost harmless...
LEFT_BRACE      : {!in_noparse}? => '{';
RIGHT_BRACE     : {!in_noparse}? => '}';

// escaped special characters are just punctuation...
ESCAPED_PUNC     : {in_noparse}? => ('#' | '*' | ':' | ';' | '|' | '[' | ']' | '=' | '/' | '{' | '}' | STUPID);

fragment
STUPID: '!$()#*%&!*%$(!#&$';

DIGIT: '0'..'9';

LETTERS    :    LETTER+;

fragment
LETTER    :    ('A'..'Z'|'a'..'z');

SPACE:    ' ';
NL    :    '\r'? '\n' {setText("\\n\n");};

/* totally harmless punctuation? */
DOT             :    '.'; // Only purpose of dot is [[image:foo.jpg]]...
UNDERSCORE      :    '_';
HYPHEN          :    '-';
COMMA           :    ',';
OPEN_PAREN      :    '(';
CLOSE_PAREN     :    ')';
PLUS            :    '+';
TILDE           :    '~';
AT              :    '@';

UNKNOWN    :    .;

/* inline HTML tags */

/*fragment
HTML_OBR : '<br' (WS ATTR)? WS? ('>' | '/>') ;*/

fragment
HTML_OPEN: '<' ALLOWED_HTML (WS ATTR)? WS? ('>' | '/>');

fragment
HTML_CLOSE: '</' ALLOWED_HTML '>';

fragment
REF_OPEN: '<ref' (WS ATTR)? WS? ('>' | '/>');

fragment
REF_CLOSE: '</ref>';



fragment
ALLOWED_HTML:
    'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'cite' | 'center' | 'blockquote' | 'caption' |  'br' /*| 'pre' -- treated specially */
    | 'b' | 'del' | 'i' | 'ins' | 'u' | 'font' | 'big' | 'small' | 'sub' | 'sup' | 'code' | 'em' | 's' | 'strike' | 'strong' | 'tt' | 'var'
    | 'ol' | 'ul' | 'dl'
    | 'p' | 'span' | 'table' | 'div'
    | 'rt' | 'rb ' | 'rp' | 'ruby'
    | 'hr' | 'li' | 'dt' | 'dd'
    | 'tr' | 'td' | 'th';