__author__="KOLANICH"
__license__="Unlicense"

from .KSAST import yamlDumper, KaitOrdEnt, ruamel
from enum import Enum

import _io
from pathlib import Path, PurePath
import bs4

import typing
from .utils import *
from .pathTracer import Registry, extractUFWBIdFromRef, PathTracerUFWB

tagNameToClassMapper = None

@ruamel.yaml.yaml_object(yamlDumper)
class SDescription(KaitOrdEnt):
	__slots__ = ("text",)
	def __init__(self, xmlTag:bs4.Tag=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.text=xmlTag.text.strip()

@ruamel.yaml.yaml_object(yamlDumper)
class STag(KaitOrdEnt):
	__slots__=("id", "name", "doc", "_parent", "name", "fillcolor", "strokecolor", "disabled", "unused","repeat", 'repeatmin', 'repeatmax', "length", "_xmlRepr")
	def __init__(self, xmlTag:bs4.Tag=None, parent:"STag"=None, parser=None, addXMLForVerification:bool=True):
		super().__init__()
		self._parent=parent
		
		if "id" in xmlTag.attrs:
			self.id=tryParseInt(xmlTag.attrs["id"])
		
		self.name=xmlTag.get("name")
		
		l=xmlTag.attrs.get("length")
		if l:
			self.length=self.parseExpression(l)
		

		self.fillcolor=xmlTag.attrs.get("fillcolor")
		self.strokecolor=xmlTag.attrs.get("strokecolor")
		self.disabled=parseBool(xmlTag.attrs.get("disabled"))
		self.unused=parseBool(xmlTag.attrs.get("unused"))
		self.doc=xmlTag.attrs.get("doc")
		
		
		if addXMLForVerification:
			self._xmlRepr=str(copyOnlyThisTag(xmlTag))
		
		
		if not self.doc:
			docTag=xmlTag.select_one("description")
			if docTag:
				self.doc = SDescription(docTag, kaitTag)
	

@ruamel.yaml.yaml_object(yamlDumper)
class SNumberAttrs(STag):
	__slots__ = ("signed", "endian", "lengthUnit")
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.endian = xmlTag.attrs.get("endian")
		self.signed = parseBool(xmlTag.attrs.get("signed"))
		self.lengthUnit=xmlTag.attrs.get("lengthunit")

def initSStringAttrs(self, xmlTag:bs4.Tag=None, parent:STag=None):
	self.encoding = xmlTag.attrs.get("encoding")

@ruamel.yaml.yaml_object(yamlDumper)
class SStringAttrs(STag):
	__slots__ = ("encoding", "delimiter")
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		initSStringAttrs(self, xmlTag, parent)

class StructureOrder(Enum):
	variable = 'variable'
	fixed = 'fixed'
	# Choose a fixed element order if all elements in the structure have to appear in a fixed order. If only a single element of many is expected, choose variable.

@ruamel.yaml.yaml_object(yamlDumper)
class SStructure(SNumberAttrs):
	__slots__ = tuple(["consistsOf", "floating", "order", "valueExpression", "debug", "alignment", "extends", "lengthOffset", "contents"]+list(SStringAttrs.__slots__)) #FUCK, __slots__ cannot into multiple inheritance
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag, parent, parser)
		initSStringAttrs(self, xmlTag, parent) #FUCK, __slots__ cannot into multiple inheritance
		
		alignment = xmlTag.attrs.get("alignment")
		if alignment:
			self.alignment=int(alignment) #If a structure must start at a multiple of n bytes, use the alignment field.
		self.consistsOf=parser.delayResolveRef(self, "consistsOf", xmlTag.attrs.get("consists-of"))
		self.extends=parser.delayResolveRef(self, "extends", xmlTag.attrs.get("extends"))  #{name, ref} Select here the structure to inherit from. Only top-level structures can inherit from other top-level structures
		self.floating=parseBool(xmlTag.attrs.get("floating"))
		
		lengthOffset=xmlTag.attrs.get("lengthoffset")
		if lengthOffset:
			self.lengthOffset=int(lengthOffset)
		
		self.order=StructureOrder(xmlTag.attrs.get("order", StructureOrder.fixed))
		self.valueExpression=xmlTag.attrs.get("valueexpression")
		self.debug=parseBool(xmlTag.attrs.get("debug"))

		self.contents=[]

		for field in fv.contents:
			if isinstance(field, bs4.Tag):
				if field.name in tagNameToClassMapper:
					ctor=tagNameToClassMapper[field.name]
				else:
					raise NotImplementedError("Tag `"+field.name+"` is not implemented!")
				kaitTag=ctor(field, self, parser)



@ruamel.yaml.yaml_object(yamlDumper)
class SGrammar(SStructure):
	__slots__ = ("start", "fileExtension", "uti", "author", "email", "complete",)
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		if "start" in xmlTag.attrs:
			self.start = parser.resolveRef(xmlTag.attrs["start"])
		
		if "filextension" in xmlTag.attrs:
			self.fileExtension=xmlTag.attrs["fileextension"].split(",")
		self.uti=xmlTag.attrs.get("uti")
		self.author=xmlTag.attrs.get("author")
		self.email=xmlTag.attrs.get("email")
		self.complete=xmlTag.attrs.get("complete")

class NumberDisplayType(Enum):
	bin='binary'
	hex='hex'
	dec='decimal'

@ruamel.yaml.yaml_object(yamlDumper)
class SNumber(SNumberAttrs):
	__slots__ = ("type", 'display','minval', 'maxval')
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.display = NumberDisplayType(xmlTag.attrs.get('display'))


class StringType(Enum):
	zeroTerminated=nullTerminated=c="zero-terminated"
	delimiterTerminated="delimiter-terminated"
	fixedLength="fixed-length"
	pascal="pascal"#For pascal strings the first character is interpreted as the actual string length. You can also specify a length that the pascal string consumes in any case, independently of the actual string length.

@ruamel.yaml.yaml_object(yamlDumper)
class SString(SStringAttrs):
	__slots__ = ("type", "delimiter")
	
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.type=StringType(xmlTag.attrs["type"])
		
		if self.type==StringType.delimiterTerminated:
			self.delimiter=tryParseInt(xmlTag.attrs["delimiter"], 16)
		

class SOffset(STag):
	__slots__ = ('relativeTo', 'additional', "references", "referencedSize", "follownullreference")
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		self.references=parser.delayResolveRef(self, "references", xmlTag.attrs["references"])
		self.referencedSize=xmlTag.get("referenced-size")
		self.relativeTo=parser.delayResolveRef(self, "relativeTo", xmlTag.attrs['relative-to'])
		self.additional=parser.parseExpression(xmlTag.attrs['additional'])
		
		fnr=xmlTag.get("follownullreference")
		if fnr:
			fnr=parseBool(fnr)
			if fnr is False or fnr is True:
				self.follownullreference = fnr
			else:
				raise ValueError("unknown value for follownullreference: "+repr(fnr))
		
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)

@ruamel.yaml.yaml_object(yamlDumper)
class SSignature(SNumber):
	__slots__ = ('mustMatch',)
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.mustMatch=xmlTag.attrs.get("mustmatch")

@ruamel.yaml.yaml_object(yamlDumper)
class SEnum(SNumberAttrs):
	__slots__ = ('mustMatch',)
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.mustMatch=xmlTag.attrs.get("mustmatch")


@ruamel.yaml.yaml_object(yamlDumper)
class SEnumValue(SNumber):
	__slots__ = ('mustMatch', "value")
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.mustMatch=xmlTag.attrs.get("mustmatch")

@ruamel.yaml.yaml_object(yamlDumper)
class SBinary(STag):
	__slots__ = ("length", )
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.length=xmlTag.get("length")
		
		return kaitTag

@ruamel.yaml.yaml_object(yamlDumper)
class SRef(STag):
	__slots__ = ("structure",)
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		structure=xmlTag.get("structure")
		if not structure:
			self.structure=transformName(xmlTag.attrs["name"])
		else:
			self.structure=parser.delayResolveRef(self, "structure", structure)

@ruamel.yaml.yaml_object(yamlDumper)
class SGrammarRef(STag):
	__slots__ = ("filename",)
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.filename=PurePath(xmlTag.attrs["filename"]).stem
		#xmlTag.attrs["name"]
		#xmlTag.attrs["uti"]


@ruamel.yaml.yaml_object(yamlDumper)
class SScript(STag):
	__slots__ = ("source","language")
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.text=xmlTag.text.strip()
		kaitTag=KField()
		src=xmlTag.select("source")
		if not src: #oops, source is not parsed because of unknown reason:
			self.source=xmlTag.text
			self.language=xmlTag.get("language")
		else:
			self.source=src.text
			self.language=src.get("language")

@ruamel.yaml.yaml_object(yamlDumper)
class SScripts(STag):
	__slots__ = ("scripts",)
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.scripts=[]
		for s in xmlTag.select("script"):
			__class__.script(converter, s, parentType)

@ruamel.yaml.yaml_object(yamlDumper)
class SCustom(STag):
	__slots__ = ("script",)
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)
		self.script=parser.delayResolveRef(self, "script", xmlTag.attrs["script"], True)

@ruamel.yaml.yaml_object(yamlDumper)
class SScriptElement(STag):
	__slots__ = ()
	def __init__(self, xmlTag:bs4.Tag=None, parent:STag=None, parser=None):
		super().__init__(xmlTag=xmlTag, parent=parent, parser=parser)

@ruamel.yaml.yaml_object(yamlDumper)
class GrammarFile(KaitOrdEnt):
	__slots__ = ("version", "grammar")
	def __init__(self, xmlTag:bs4.Tag, parser):
		super().__init__()
		self.version=xmlTag.attrs.get("version")
		
		gs = list(xmlTag.select("grammar"))
		assert len(gs) == 1
		g = gs[0]
		self.grammar=SGrammar(g, None, parser=parser)

class RefDelayedResolve():
	__slots__=("obj", "propName", "refValue", "args", "kwargs")
	def __init__(self, obj:typing.Any, propName:str, refValue:str, *args, **kwargs):
		self.obj = obj
		self.propName = propName
		self.refValue = refValue
		self.args=args
		self.kwargs=kwargs
	
	def __call__(self, resolver):
		resolved = resolver.resolveRef(self.refValue, *self.args, **self.kwargs)
		setattr(self.obj, self.propName, resolved)
		self.refValue = self.propName = self.obj = None

class GrammarParser:
	def __init__(self):
		self.tracer = PathTracerUFWB()
		self.delayedResolves = []
		self.addXMLForVerification=False
	
	def parse(self, grammarFile:typing.Union[_io._IOBase, str, bs4.BeautifulSoup]):
		if isinstance(grammarFile, Path):
			with grammarFile.open("rt", encoding="utf-8") as f:
				return self.parse(f)
		if isinstance(grammarFile, _io._IOBase):
			grammarFile=grammarFile.read()
		if isinstance(grammarFile, str):
			grammarFile=xmlStr2BS4(grammarFile)
		
		res = GrammarFile(grammarFile, parser=self)
		
		for delayedResolve in self.delayedResolves:
			delayedResolve(self)
		self.delayedResolves = None
		return res
	
	def delayResolveRef(self, obj:typing.Any, propName:str, refValue:str, *args, **kwargs):
		if refValue is not None:
			res = RefDelayedResolve(obj, propName, refValue, *args, **kwargs)
			self.delayedResolves.append(res)
			return res
		
	
	def resolveRef(self, mayBeRef:str, hard:bool=False, name=False):
		return self.tracer.resolveRef(mayBeRef=mayBeRef, hard=hard, name=name)
	
	
	def parseExpression(self, expr:str) -> str:
		expr=expr.strip()
		exprParts=expressionSplittingRx.split(expr)
		if len(exprParts) == 1:
			try:
				return int(expr)
			except:
				pass
		
		for i, p in enumerate(exprParts):
			if not i%2:
				exprParts[i]=self.resolveRef(p, hard=False, name=True)
			else:
				pass
		return "".join(exprParts)
		
		#TODO: transforming expressions, need to know exact grammar and meaning of special names like prev and this (prev probably means "previously parsed in this structure", but what does this mean in this case)
		a=ast.parse(expr, mode="eval") #
		walk=[a]
		while walk:
			newWalk=[]
			for n in walk:
				if isinstance(n, ast.Name):
					n.id=self.resolveRef(n.id, hard=False, name=True)
				else:
					if isinstance(n, ast.AST):
						for fN in n._fields:
							f=getattr(n, fN)
							newWalk.append(f)
			walk=newWalk
		return astor.unparse(a)


def nonMaskNumberProcessing(converter, fv, parentType, kaitTag, sizeDescriptor, enumBitShift:int=0):
	endianness = getEndianness(fv, parentType, True)
	if not makeSignatureOrIntEnumIfEnum(converter, fv, parentType, kaitTag, int, enforceSignatureIfSingle=False, sizeDescriptor=sizeDescriptor, enumBitShift=enumBitShift, endianness=endianness):
		endiannessImmediate = getEndianness(fv, None, False)
		kaitTag.type=getNumberType(fv, sizeDescriptor, endiannessImmediate, parentType=parentType)
	
	if parseBool(fv.attrs.get("mustmatch")):
		boolExprConcat(kaitTag, "-assert", "true", "and")
		if 'minval' in fv.attrs:
			boolExprConcat(kaitTag, "-assert", fv.attrs['minval']+" <= _", "and")
		if 'maxval' in fv.attrs:
			boolExprConcat(kaitTag, "-assert", "_ <= " +fv.attrs['maxval'], "and")


tagNameToClassMapper = {
	"number":SNumber,
	"string":SString,
	"description":SDescription,
	"binary":SBinary,
	"structref":SRef,
	"offset":SOffset,
	"script":SScript,
	"scripts":SScripts,
	"custom":SCustom,
	"scriptelement":SScriptElement,
	"grammarref":SGrammarRef,
}
