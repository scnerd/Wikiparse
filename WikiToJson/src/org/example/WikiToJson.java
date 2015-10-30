package org.example;

//import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;

import org.sweble.wikitext.lazy.parser.*;
import org.sweble.wikitext.lazy.preprocessor.*;
import org.sweble.wikitext.lazy.utils.XmlAttribute;
import org.sweble.wikitext.lazy.utils.XmlAttributeGarbage;
import org.sweble.wikitext.lazy.utils.XmlCharRef;
import org.sweble.wikitext.lazy.utils.XmlEntityRef;
//import org.apache.commons.io.FileUtils;
import org.sweble.wikitext.engine.CompiledPage;
import org.sweble.wikitext.engine.Compiler;
import org.sweble.wikitext.engine.CompilerException;
import org.sweble.wikitext.engine.PageId;
import org.sweble.wikitext.engine.PageTitle;
import org.sweble.wikitext.engine.utils.SimpleWikiConfiguration;
import org.sweble.wikitext.lazy.LinkTargetException;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.Stack;

import de.fau.cs.osr.ptk.common.VisitingException;
import de.fau.cs.osr.ptk.common.Visitor;
import de.fau.cs.osr.ptk.common.ast.AstNode;
import de.fau.cs.osr.ptk.common.ast.NodeList;
import de.fau.cs.osr.ptk.common.ast.Text;

import org.sweble.wikitext.engine.Page;

import com.google.gson.JsonArray;
import com.google.gson.JsonPrimitive;
import com.google.gson.JsonObject;
import com.google.gson.GsonBuilder;

import py4j.GatewayServer;
import py4j.Py4JNetworkException;

@SuppressWarnings("deprecation")
public class WikiToJson extends Visitor {
	
	private WikiPage curPage = null;
	private static Context curContext = null;

	private class WikiPage {
		public Context root, refs;
		public ArrayList<ContextPointer> internalLinks = new ArrayList<ContextPointer>();
		public ArrayList<ContextPointer> externalLinks = new ArrayList<ContextPointer>();
		public ArrayList<ContextPointer> sections = new ArrayList<ContextPointer>();
		
		public JsonObject toJson() {
			JsonObject json = new JsonObject();
			json.add("root", root.toJson());
			json.add("refs", refs.toJson());
			
			JsonArray internals = new JsonArray();
			for(ContextPointer item : internalLinks) {
				internals.add(item.toJson());
			}
			
			JsonArray externals = new JsonArray();
			for(ContextPointer item : externalLinks) {
				externals.add(item.toJson());
			}
			
			JsonArray jsonSections = new JsonArray();
			for(ContextPointer item : sections) {
				jsonSections.add(item.toJson());
			}
			
			json.add("internal_links", internals);
			json.add("external_links", externals);
			json.add("sections", jsonSections);
			
			return json;
		}
	}

	private static abstract class PageElement {
		private static int S_ID;
		protected int id = S_ID++;
		
		public static void initialize() {
			S_ID = 1;
		}
		
		// Possible types:
		public static final String
		CONTEXT = "context",
		TEXT = "text",
		INTERNAL_LINK = "internal_link",
		EXTERNAL_LINK = "external_link",
		HEADING = "heading",
		SECTION = "section",
		IMAGE = "image",
		TEMPLATE = "template",
		REDIRECTION = "redirection",
		POINTER = "pointer",
		TEMPLATE_ARG = "template_arg";

		public String type;
		public Context parent;

		public PageElement() {
			parent = curContext;
		}
		
		protected String toString(String content)
		{
			return type + "(" + content + ")";
		}
		
		public abstract String allText();
		
		public JsonObject toJson() {
			JsonObject json = new JsonObject();
			json.addProperty("id", id);
			json.addProperty("type", this.type);
			return json;
		}
		
		public String checkString(String s)
		{ return s == null ? "" : s; }
	}

	private class Context extends PageElement {		
		public static final String
		CTXT_REGULAR = "",
		CTXT_LINK = "__link_",
		CTXT_HEADING = "__heading_",
		CTXT_IMAGE = "__image_",
		CTXT_SECTION = "__section_",
		CTXT_TEMPLATE = "__template_",
		CTXT_POINTER = "__pointer";

		public String label;
		public LinkedList<PageElement> content;

		public Context(String label) {
			super();
			type = CONTEXT;
			this.label = CTXT_REGULAR + label;
			content = new LinkedList<PageElement>();
		}
		
		public String toString() {
			return this.toString("");
		}
		
		public String toString(String indent)
		{
			String children = "\n";
			indent += "  ";
			for(PageElement child : content)
				children += indent + 
					(Context.class.isAssignableFrom(child.getClass()) ? child.toString(indent) : child.toString()) +
					(child != content.get(content.size() - 1) ? ", " : "") +
					"\n";
			return super.toString(label + ": [" + children + indent + "]");
		}
		
		public String allText()
		{
			String children = "";
			for(PageElement child : content)
				children += child.allText();
			return children;
		}
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.addProperty("label", label);
			if(content != null) {
				JsonArray children = new JsonArray();
				for(PageElement child : content) {
					children.add(child.toJson());
				}
				json.add("children", children);
			}
			return json;
		}
	}
	
	private class ContextPointer extends Context {
		public Context context;
		
		public ContextPointer(Context ctxt) {
			super(CTXT_POINTER + ctxt.label);
			this.context = ctxt;
			this.content = null;
			this.type = POINTER;
		}
		
		public String toString(String indent) {
			return "";
		}
		
		public String allText() {
			return "";
		}
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.addProperty("target", context.id);
			return json;
		}
	}

	public Stack<String> curTextProperties;
	public int textPropNumber = 1;

	private class TextElement extends PageElement {

		public String text;
		public String[] properties;

		public TextElement(String txt) {
			super();
			type = TEXT;
			text = txt;
			properties = curTextProperties.toArray(new String[curTextProperties
					.size()]);
		}
		
		public String toString()
		{
			String props = "";
			for(String prop : properties)
				props += prop.toString() + (prop != properties[properties.length - 1] ? ", " : "");
			return "\"" + text + "\" {" + props + "}";
		}
		
		public String allText()
		{
			return text;
		}
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.addProperty("text", text);
			JsonArray jsonProperties = new JsonArray();
			for(String prop : properties) {
				jsonProperties.add(new JsonPrimitive(prop));
			}
			json.add("properties", jsonProperties);
			return json;
		}
	}

	public class LinkElement extends Context {
		public String target;
		private TextElement defaultText;

		public LinkElement(String target, boolean internal) {
			super(CTXT_LINK + (target == null ? "" : target));
			type = internal ? INTERNAL_LINK : EXTERNAL_LINK;
			this.target = target;
			
			(internal ? curPage.internalLinks : curPage.externalLinks).add(new ContextPointer(this));
			defaultText = new TextElement(target);
		}
		
		public String toString(String indent)
		{
			if(content.size() == 0)
				return indent + "  " + defaultText.toString();
			return super.toString(indent);
		}
		
		public String allText()
		{
			if(content.size() == 0)
				return defaultText.allText();
			return super.allText();
		}
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.addProperty("target", target);
			json.add("default_text", defaultText.toJson());
			return json;
		}
	}

	public class HeadingElement extends Context {
		public int level;

		public HeadingElement(int level) {
			super(CTXT_HEADING + Integer.toString(level));
			type = HEADING;
			this.level = level;
		}
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.addProperty("level", level);
			return json;
		}
	}

	public class SectionElement extends Context {
		public int level;
		public Context title, body;

		public SectionElement(int level, Context title, Context body) {
			super(CTXT_SECTION + Integer.toString(level));
			type = SECTION;
			this.level = level;
			this.title = title;
			this.body = body;
			
			curPage.sections.add(new ContextPointer(this));
			
			//this.content.add(this.body);
		}
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.addProperty("level", level);
			json.add("title", title.toJson());
			json.add("body", body.toJson());
			return json;
		}
	}

	public class ImageElement extends Context {
		public String linkPage;
		public String linkUrl;
		public String target;
		public ContextPointer title;

		public ImageElement(String linkPage, String linkUrl, String target,
				Context title) {
			super(CTXT_IMAGE + (title == null ? "" : title));
			type = IMAGE;
			this.linkPage = linkPage;
			this.linkUrl = linkUrl;
			this.target = target;
			this.title = new ContextPointer(title);
			
			this.content.add(title);
		}
		
		public String allText()
		{ return ""; }
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.addProperty("link_page", checkString(linkPage));
			//json.addProperty("JUNK", "!@#$");
			json.addProperty("url", linkUrl);
			json.addProperty("target", target);
			json.add("title", title.toJson());
			return json;
		}
	}
	
	public class TemplateElement extends Context {
		public Context title;
		
		public TemplateElement(Context title) {
			super(CTXT_TEMPLATE);
			type = TEMPLATE;
			this.title = title;
		}
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.add("title", title.toJson());
			return json;
		}
	}
	
	public class RedirectionElement extends TextElement {
		public static final String REDIR_PROP = "redirection";
		
		public String target;
		
		public RedirectionElement(String target)
		{
			super(target);
			type = REDIRECTION;
			this.target = target;
			this.properties = new String[]{REDIR_PROP};
		}
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.addProperty("target", this.target);
			return json;
		}
	}
	
	public class TemplateArgumentElement extends Context {
		public ContextPointer name;
		public ContextPointer value;
		
		public TemplateArgumentElement(Context name, Context value) {
			super(CTXT_TEMPLATE + "arg");
			type = TEMPLATE_ARG;
			this.name = new ContextPointer(name);
			this.value = new ContextPointer(value);
			
			this.content.add(name);
			this.content.add(value);
		}
		
		public JsonObject toJson() {
			JsonObject json = super.toJson();
			json.add("name", name.toJson());
			json.add("value", value.toJson());
			return json;
		}
	}

	// =========================================================================

	public WikiToJson() {
	}

	@Override
	protected boolean before(AstNode node) {
		
		PageElement.initialize();
		
		curTextProperties = new Stack<String>();
		curPage = new WikiPage();
		curPage.refs = new Context("refs");
		curContext = curPage.root = new Context("page");
		curContext = new Context("__root");
		curPage.root.content.add(curContext);

		return super.before(node);
	}

	@Override
	protected Object after(AstNode node, Object result) {
		return curPage;
	}

	// =========================================================================
	// COMMON
	// =========================================================================

	public void visit(AstNode n) {
		// Fallback for all nodes that are not explicitly handled below
		iterate(n);
	}

	public void visit(NodeList n) {
		Context storedCurContext = curContext;
		int inXmlRefCt = 0;
		
		// Loop through the children, with one caveat
		for(AstNode child : n) {
			try {
				/* XmlEntityRefs are supposed to come in sets of four at the same level.
				 * The first marks the "<" that starts an xml-tagged reference (_<_ref>url description</ref>)
				 * Following content should be discarded, and thus is added to a discarded context (just the "ref" text)
				 * The second marks the next ">" that ends the opening tag     (<ref_>_url description</ref>)
				 * Following content should be stored as a special reference, with a pointer to that reference in text
				 * The third marks the "<" that starts the closing tag         (<ref>url description_<_/ref>)
				 * Like the first, following content should be discarded (the "/ref" text)
				 * The fourth marks the ">" that closes the closing tag        (<ref>url description</ref_>_)
				 * At this part, resume parsing where you left off 
				 */
				if(XmlEntityRef.class.isAssignableFrom(child.getClass())) {
					inXmlRefCt = (inXmlRefCt + 1) % 4;
					if(inXmlRefCt == 1)
					{
						curContext = new Context("JUNK");
					}
					else if(inXmlRefCt == 2)
					{
						curContext = new Context("ref_" + ((XmlEntityRef)child).getName());
						curContext.parent = curPage.refs;
						storedCurContext.content.add(new ContextPointer(curContext));
						curPage.refs.content.add(curContext);
					}
					else if(inXmlRefCt == 3)
					{
						curContext = new Context("JUNK");
					}
					else if(inXmlRefCt == 0)
					{
						curContext = storedCurContext;
					}
				}
				dispatch(child);
			}
			catch(VisitingException ex) { System.out.println("Error encountered with a node of type " + child.getClass().getName()); }
		}
		if (inXmlRefCt != 0)
			visit(new Text("\n"));
		curContext = storedCurContext;
	}

	public void visit(Page p) {
		iterate(p.getContent());
	}

	public void visit(Text text) {
		String ctnt = text.getContent();
		curContext.content.add(new TextElement(ctnt == null ? "" : ctnt));
	}
	
	public void visit(String str) {
		visit(new Text(str));
	}

	/**
	 * Adds the specified property to all text contained in the given node
	 * @param property The property to tag text with
	 * @param toIterate The node to continue parsing with
	 */
	private void textProperty(String property, AstNode toIterate) {
		if(toIterate != null) {
			int num = textPropNumber++;
			property = String.format("%s(%d)", property, num);
			curTextProperties.push(property);
			iterate(toIterate);
			curTextProperties.pop();
		}
	}
	
	/**
	 * Uses the specified context as the context in which to parse the given node, adding to the current context
	 * @param newContext The context to parse within (gets set as curContext while parsing the given node)
	 * @param toIterate The AstNode to parse within the specified context
	 */
	private void enterContext(Context newContext, AstNode toIterate) {
		curContext.content.add(newContext);
		enterNewContext(newContext, toIterate);
	}
	
	/**
	 * Uses the specified context as the context in which to parse the given node
	 * @param newContext The context to parse within (gets set as curContext while parsing the given node)
	 * @param toIterate The AstNode to parse within the specified context
	 */
	private void enterNewContext(Context newContext, AstNode toIterate) {
		Context prevContext = curContext;
		if(toIterate != null) {
			curContext = newContext;
			iterate(toIterate);
			curContext = prevContext;
		}
	}

	// =========================================================================
	// PARSER
	// =========================================================================
	public void visit (Bold bold) { textProperty("bold", bold); }
	public void visit (DefinitionDefinition definitionDefinition) { textProperty("def", definitionDefinition); }
	public void visit (DefinitionList definitionList) { textProperty("defList", definitionList); }
	public void visit (DefinitionTerm definitionTerm) { textProperty("term", definitionTerm); }
	public void visit (Enumeration enumeration) { textProperty("enum", enumeration); }
	public void visit (EnumerationItem enumerationItem) { textProperty("enumItem", enumerationItem); }
	public void visit (ExternalLink externalLink) { enterContext(new LinkElement(externalLink.getTarget().getPath(), false), externalLink.getTitle()); }
	public void visit (Heading heading) { enterContext(new HeadingElement(heading.getLevel()), heading); }
	public void visit (HorizontalRule horizontalRule) { iterate(horizontalRule); }
	//public void visit (ImageHorizAlign imageHorizAlign) { }
	public void visit(ImageLink imageLink) {
		Context title = new Context(Context.CTXT_IMAGE + "title");
		
		Url url = imageLink.getLinkUrl();
		Context ctxt = new ImageElement(imageLink.getLinkPage(), url == null ? "" : url.getPath(), imageLink.getTarget(), title);
		
		enterNewContext(title, imageLink.getTitle());
		enterContext(ctxt, imageLink);
		
		title.parent = ctxt;
		
	}
	//public void visit (ImageVertAlign imageVertAlign) { }
	//public void visit (ImageViewFormat imageViewFormat) { }
	public void visit (InternalLink internalLink) {
		String target = internalLink.getTarget();
		LinkTitle title = internalLink.getTitle();
		LinkElement le = new LinkElement(target, true);
		if(title != null) {
			NodeList titleContent = title.getContent();
			enterContext(le, titleContent);
		}
		else {
			curContext.content.add(le);
		}
	}
	public void visit (Italics italics) { textProperty("italics", italics); }
	public void visit (Itemization itemization) { textProperty("items", itemization); }
	public void visit (ItemizationItem itemizationItem) { visit(new Text("\n")); textProperty("itemsItem", itemizationItem); }
	//public void visit (LinkOptionAltText linkOptionAltText) { }
	//public void visit (LinkOptionGarbage linkOptionGarbage) { }
	//public void visit (LinkOptionKeyword linkOptionKeyword) { }
	//public void visit (LinkOptionLinkTarget linkOptionLinkTarget) { }
	//public void visit (LinkOptionResize linkOptionResize) { }
	public void visit (LinkTarget linkTarget) { curContext.content.add(new TextElement(linkTarget.getContent())); }
	public void visit (LinkTitle linkTitle) { textProperty("link", linkTitle);  }
	public void visit (MagicWord magicWord)
	{
		curTextProperties.push("magic");
		curContext.content.add(new TextElement(magicWord.getWord()));
		curTextProperties.pop();
	}
	//public void visit (Paragraph paragraph) { }
	//public void visit (RawListItem rawListItem) { }
	public void visit (Section section) {
		Context title = new Context(Context.CTXT_SECTION + "title");
		Context body = new Context(Context.CTXT_SECTION + "body");
		
		enterNewContext(title, section.getTitle());
		enterNewContext(body, section.getBody());
		
		Context ctxt = new SectionElement(section.getLevel(), title, body);
		title.parent = body.parent = ctxt;
		curContext.content.add(ctxt);
	}
	//public void visit (SemiPre semiPre) { }
	//public void visit (SemiPreLine semiPreLine) { }
	public void visit (Signature signature) { return; }
	public void visit (Table table) { textProperty("table", table); }
	public void visit (TableCaption tableCaption) { textProperty("tableCaption", tableCaption); }
	public void visit (TableCell tableCell) { textProperty("tableCell", tableCell); }
	public void visit (TableHeader tableHeader) { textProperty("tableHeader", tableHeader); }
	public void visit (TableRow tableRow) { textProperty("tableRow", tableRow); }
	public void visit (Ticks ticks) { return; }
	public void visit (Url url)
	{
		curTextProperties.push("url");
		curContext.content.add(new TextElement(url.getPath()));
		curTextProperties.pop();
	}
	//public void visit (Whitespace whitespace) {  }
	public void visit (XmlElement xmlElement) { textProperty("xml", xmlElement); }
	public void visit (XmlElementClose xmlElementClose) { textProperty("xmlClose", xmlElementClose); }
	public void visit (XmlElementEmpty xmlElementEmpty) { textProperty("xmlEmpty", xmlElementEmpty); }
	public void visit (XmlElementOpen xmlElementOpen) { textProperty("xmlOpen", xmlElementOpen); }

	// =========================================================================
	// PREPROCESSOR
	// =========================================================================
	public void visit (Template template) {
		Context title = new Context(Context.CTXT_TEMPLATE + "title");
		Context ctxt = new TemplateElement(title);
		
		enterNewContext(title, template.getName());
		enterNewContext(ctxt, template.getArgs());
		
		title.parent = ctxt;
		ctxt.parent = curPage.root;
		curPage.root.content.add(ctxt);
	}
	public void visit(TemplateArgument templateArgument) {
		Context name = new Context(Context.CTXT_TEMPLATE + "arg_name");
		Context value = new Context(Context.CTXT_TEMPLATE + "arg_value");
		Context ctxt = new TemplateArgumentElement(name, value);
		
		enterNewContext(name, templateArgument.getName());
		enterNewContext(value, templateArgument.getValue());
		
		name.parent = value.parent = ctxt;
		// Don't visit the sub-elements, you'll end up duplicating the inner data... elsewhere too?
		curContext.content.add(ctxt);
	}
	public void visit(TemplateParameter templateParameter) { textProperty("tempParameter", templateParameter); }
	public void visit(Redirect redirect) { curPage.root.content.add(0, new RedirectionElement(redirect.getTarget())); }
	public void visit(TagExtension tagExtension)
	{
		switch(tagExtension.getName().toLowerCase()) {
		case "ref":
			Context ref = new Context("tag_extension_ref");
			ref.parent = curPage.refs;
			curContext.content.add(ref);
			enterNewContext(ref, tagExtension.getXmlAttributes());
			break;
		default:
			curTextProperties.push("tag_extension_" + tagExtension.getName());
			curContext.content.add(new TextElement(tagExtension.getBody()));
			curTextProperties.pop();
			break;
		}
	}
	public void visit(Ignored ignored) { return; }
	public void visit(XmlComment xmlComment) { return; }

	// =========================================================================
	// UTILITY
	// =========================================================================
	public void visit(XmlAttributeGarbage xmlAttributeGarbage) { }
	public void visit(XmlEntityRef xmlEntityRef) { textProperty("xmlEntRef", xmlEntityRef); }
	public void visit(XmlCharRef xmlCharRef) { textProperty("xmlCharRef", xmlCharRef); }
	public void visit(XmlAttribute xmlAttribute) { }

	// ****************************************************************************

	/* Command-line execution code
	public static void trial_run(String[] args) throws FileNotFoundException,
			IOException, LinkTargetException, CompilerException {
		if (args.length < 1) {
			System.err.println("Usage: java -jar WikiToJson.jar TITLE [-p]");
			System.err.println();
			System.err
					.println("  The program will look for a file called `TITLE.wikitext',");
			System.err
					.println("  parse the file and write a JSON version to `TITLE.json'.");
			System.err
					.println("p - Turns on pretty printing for the JSON output");
			return;
		}

		String fileTitle = args[args.length - 1].equals("-p") ? args[args.length - 2] : args[args.length - 1];

		System.out.println("Parsing...");
		WikiPage page = run(FileUtils.readFileToString(new File(fileTitle + ".wikitext")));

		System.out.println("Writing...");
		GsonBuilder gson_builder = new GsonBuilder();
		if(args[args.length - 1].equals("-p"))
			gson_builder.setPrettyPrinting();
		File f = new File(fileTitle + ".json");
		FileUtils.writeStringToFile(f, gson_builder.create().toJson(page.toJson()));
		
		System.out.println("Done, output saved to " + f.getAbsolutePath());
	}
	*/
	static GatewayServer gateway = null;
	public class ParseTools {

		public String convertWikitextToJson(String wikitext)
				throws LinkTargetException, CompilerException,
				FileNotFoundException, IOException {
			return new GsonBuilder().create().toJson(run(wikitext).toJson());
		}

		public String cleanedWikitext(String wikitext) {
			return wikitext.replaceAll("&nbsp;", " ");
		}

		public WikiPage run(String wikitext) throws LinkTargetException,
				CompilerException, FileNotFoundException, IOException {
			// Set-up a simple wiki configuration
			SimpleWikiConfiguration config = new SimpleWikiConfiguration(
					"classpath:/org/sweble/wikitext/engine/SimpleWikiConfiguration.xml");

			// Instantiate a compiler for wiki pages
			Compiler compiler = new Compiler(config);

			PageId pageId = new PageId(/* Page title */PageTitle.make(config,
					"TITLE"), /* Revision */-1);

			wikitext = cleanedWikitext(wikitext);

			// Compile the retrieved page
			CompiledPage cp = compiler.postprocess(pageId, wikitext, null);

			WikiToJson p = new WikiToJson();

			try {
				return (WikiPage) p.go(cp.getPage());
			} catch (Exception ex) {
				String stackTrace = "";
				for (StackTraceElement el : ex.getStackTrace())
					stackTrace += el.toString() + "\n";
				System.out.print("=== FAILED ===\n" + p.curPage.root.toString()
						+ "\n" + stackTrace + ex.toString() + "\n"
						+ ex.getMessage() + "\n=== FAILED ===\n");
				System.exit(1);
			}
			return null;
		}
		
		public void shutdown() {
			gateway.shutdown();
		}
	}
	
	public static void main(String[] args) {
		int port = 25333;
		int plus = 0;
		while(gateway == null)
			try {
				gateway = new GatewayServer(new WikiToJson().new ParseTools(), port + plus);
			} catch (Py4JNetworkException ex) {
				if(plus < 1000)
					plus++;
				else
					throw ex;
			}
		gateway.start();
		System.out.println("Gateway launched");
		System.out.flush();
		System.out.close(); // Marks that the gateway is ready, allows stdout to be read entirely (easier in python)
	}
}
