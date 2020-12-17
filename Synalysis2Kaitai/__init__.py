import re, _io
from pathlib import Path, PurePath
from functools import partial
import struct

import bs4

import typing
from .utils import *
from .KSAST import *
from .enum import *
from .number import *
from .pathTracer import Registry, extractUFWBIdFromRef

expressionSplittingRx=re.compile("([^\\w\\.]+)")

def subStructRef(coll:typing.Union[typing.Dict[str, KTag], typing.Iterable[typing.Tuple[str, KTag]]], mayBeRef:str) -> KTag:
	id=extractUFWBIdFromRef(mayBeRef)
	
	if isinstance(coll, (dict, DictT)):
		coll=coll.items()
	else:
		coll=enumerate(coll)
	
	if id:
		matching=[el for el in coll if el[1]._additional["-ufwb-id"] == id]
		assert len(matching) == 1, "found "+str(len(matching))+" items with the same id `"+str(id)+"`, must be 1 (unique match)"
	else:
		#it is a name
		matching=[el for el in coll if el[1]._additional["-orig-id"] == mayBeRef]
		assert len(matching) == 1, "found "+str(len(matching))+" items with the same name `"+str(mayBeRef)+"`, must be 1 (unique match)"
	
	
	#print(matching[0])
	return matching[0]

def removeOrigIdIfUnneeded(kaitTag, name):
	if "-orig-id" in kaitTag._additional and kaitTag._additional["-orig-id"] == name:
		del(kaitTag._additional["-orig-id"])


offsetNamePreprocessRx=re.compile("(offset|offst|ofst|ptr|pointer|address|addr)", re.I)

def makeAPairOfNamesForPosInstance(name:str, parentType)->(str, str):
	#name=cleanLastMatchFromStr(offsetNamePreprocessRx, name) # will cause problems with resolution
	
	instanceName=processName(name, parentType.instances)
	ptrName=processName(name+"_ptr", parentType.seq)
	
	return (ptrName, instanceName)

def boolExprConcat(self, paramName:str, additionalExpr:str, operator:str="and"):
	prevExpr=self[paramName]
	if not prevExpr:
		rightSide=""
	else:
		rightSide=" "+operator+" ("+prevExpr+")"
	self[paramName]=additionalExpr+rightSide

from rangeslicetools import srev, slen

class DetectedMaskDescriptor:
	__slots__=("name", "slice", "element")
	def __init__(self, name:str, slc:slice, element:bs4.Tag):
		self.name = name
		self.slice = slc
		self.element = element
	
	def reverseSlice(self):
		self.slice = srev(self.slice)
	
	def __len__(self):
		return slen(self.slice)
	
	def __repr__(self):
		return self.__class__.__name__+"("+", ".join(repr(getattr(self, elName)) for elName in self.__class__.__slots__)+")"
	
	def __gt__(self, other):
		return self.slice.stop > other.slice.stop
	
	def __lt__(self, other):
		return self.slice.stop < other.slice.stop

def detectMasks(fv:bs4.Tag) -> typing.List[typing.Tuple[str, slice, bs4.Tag]]:
	masks=[c for c in fv.children if c.name=="mask"]
	totalBitRanges=[]
	if masks:
		for mask in masks:
			descr=mask.attrs.get("descr")
			bitsRanges=maskToBitRanges(tryParseInt(mask.attrs.get("value")))
			if len(bitsRanges)!=1:
				return None
			
			totalBitRanges.append(DetectedMaskDescriptor(mask.attrs.get("name"), bitsRanges[0], mask))
		return totalBitRanges
	else:
		return None

from Endianness import EndiannessMapping, wellKnown

def generateBitType(converter, parsedMasks:typing.List[typing.Tuple[str, slice, bs4.Tag]], typeBitSize:int, endianness:typing.Optional[str]=None):
	enclosingType=KType()
	
	if not endianness:
		endianness = "le"
		warnings.warn("Unknown endianness for a bit-sized type. Assumming `"+endianness+"`")
	
	if endianness == "dynamic":
		endianness = "le"
		# TODO: generate dynamic enum
		#beEnum = generateBitType(converter, parsedMasks, typeBitSize, "be")
		#leEnum = generateBitType(converter, parsedMasks, typeBitSize, "le")
		
	
	m = EndiannessMapping(wellKnown[endianness], typeBitSize)
	#print("m.forward.tree", m.forward.tree)
	
	for maskDescr in parsedMasks:
		maskDescr.reverseSlice()
	
	parsedMasksNew=[]
	for maskDescr in parsedMasks:
		#print("maskDescr.slice", maskDescr.slice)
		currentMaskMapping = tuple(m.encode(maskDescr.slice))
		#print("currentMaskMapping", maskDescr.name, currentMaskMapping)
		if not currentMaskMapping:
			warnings.warn(
				"Endianness-remapped ranges for `"+maskDescr.name+"` are empty." +
				((" May be a size issue: this bit-field is occupies bits " + str(maskDescr.slice.start) + ":" + str(maskDescr.slice.stop) + " but the containing field is only " + str(typeBitSize) + " bits") if typeBitSize < maskDescr.slice.start else "")
			)
		elif len(currentMaskMapping) == 1:
			maskDescr.name = processName(maskDescr.name, enclosingType.seq)
			parsedMasksNew.append(DetectedMaskDescriptor(maskDescr.name, currentMaskMapping[0].indexee, maskDescr.element))
		else:
			inst=KInstance()
			inst.value = None
			
			for i, subMap in enumerate(currentMaskMapping):
				maskDescr.name=processName(maskDescr.name, enclosingType.instances)
				newName = processName(maskDescr.name + "_" + str(i), enclosingType.seq)
				parsedMasksNew.append(DetectedMaskDescriptor(newName, subMap.indexee, maskDescr.element))
				
				if inst.value is None:
					inst.value = newName
				else:
					inst.value = "("+inst.value+") << "+str(slen(subMap.indexee))+" | " + newName
			# bug - not a enum, instead its parts are enums
			enclosingType.instances[maskDescr.name]=inst
	
	if not parsedMasksNew:
		return None
	
	#print("parsedMasksNew", parsedMasksNew)
	parsedMasksNew.sort(reverse=True)
	
	#print("parsedMasksNew sorted", parsedMasksNew)
	
	lastReserved=0
	
	def genReserved(l):
		nonlocal lastReserved
		f=KField()
		f.id="reserved"+str(lastReserved)
		f.type="b"+str(l)
		enclosingType.seq.append(f)
		lastReserved+=1
	
	lastIdx=parsedMasksNew[0].slice.start
	for maskDescr in parsedMasksNew:
		maskDescr.slice.start
		print(maskDescr.slice, maskDescr.slice.start, maskDescr.slice.stop)
		l = len(maskDescr)
		#print(maskDescr, "lastIdx=", lastIdx, maskDescr.slice.start!=lastIdx, maskDescr.slice.start-lastIdx)
		if maskDescr.slice.start!=lastIdx:
			genReserved(lastIdx-maskDescr.slice.start)
		
		f=Processors.number(converter, maskDescr.element, enclosingType, sizeDescriptor=NumberSizeDescriptor(l, True), enumBitShift=maskDescr.slice.stop+1)
		f.id = maskDescr.name
		lastIdx = maskDescr.slice.stop
		enclosingType.seq.append(f)
		
	if lastIdx != -1:
		genReserved(lastIdx+1)
	return enclosingType


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


class Processors:
	"""The class containing functions with the names of tags in *.grammar XML files. When a tag met the corresponding function is called"""
	
	def number(converter, fv:bs4.Tag, parentType:KType, sizeDescriptor=None, enumBitShift=0) -> KField:
		kaitTag=KField()
		detectedMasks=detectMasks(fv)
		
		if detectedMasks:
			#print("detectedMasks", detectedMasks)
			sizeDescriptor = getNumberSize(fv, True)
			endianness = getEndianness(fv, parentType, True, None) # we need it to create the layout
			bitType = generateBitType(converter, detectedMasks, sizeDescriptor.size, endianness)
			if bitType is not None:
				if kaitTag.id is None:
					kaitTag.id=processName(fv["name"], parentType.seq)
				
				parentType.types[kaitTag.id]=bitType
				kaitTag.type=kaitTag.id
			else:
				nonMaskNumberProcessing(converter, fv, parentType, kaitTag, sizeDescriptor, enumBitShift=enumBitShift)
			
		else:
			nonMaskNumberProcessing(converter, fv, parentType, kaitTag, sizeDescriptor, enumBitShift=enumBitShift)
			
		
		kaitTag._additional["-display"]=fv.attrs.get('display') #{'binary', 'hex', 'decimal'}
		converter.processProperty(fv, kaitTag)
		kaitTag.size=None # redundant for a number and breaks bit-sized types
		return kaitTag
	
	stringTypeMapping={
		"zero-terminated": "strz",
		"delimiter-terminated": "strz",
		"fixed-length": "str",
		"pascal": "pas_str", #For pascal strings the first character is interpreted as the actual string length. You can also specify a length that the pascal string consumes in any case, independently of the actual string length.
	}
	
	def string(converter, fv:bs4.Tag, parentType:KType) -> KField:
		kaitTag=KField()
		tp=fv.attrs["type"]
		terminator=0
		
		if tp=="delimiter-terminated":
			terminator=tryParseInt(fv.attrs["delimiter"], 16)
		
		if makeSignatureOrIntEnumIfEnum(converter, fv, parentType, kaitTag, str, enforceSignatureIfSingle=True):
			if tp.endswith("terminated"):
				kaitTag.contents.append(terminator)
			elif tp=="pascal":
				kaitTag.contents.insert(0, len(contents))
		else:
			kaitTag.type=__class__.stringTypeMapping[tp]
			if tp=="delimiter-terminated":
				kaitTag._additional["terminator"]=terminator
			
			if "encoding" in fv.attrs:
				kaitTag.encoding=fv.attrs["encoding"].lower()
			if kaitTag.encoding is not None and "utf" in kaitTag.encoding:
				kaitTag.encoding += getEndianness(fv, parentType) # Unicode without endianness is disallowed, not inherited, so always needed
		
		converter.processProperty(fv, kaitTag)
		return kaitTag
	
	def grammar(converter, fv:bs4.Tag, parentType:KType) -> KType:
		gr=KType()
		__class__.structure(converter, fv, parentType, gr)
		
		gr.meta.id=processName(fv["name"], parentType.types)
		removeOrigIdIfUnneeded(gr.meta, gr.meta.id)
		
		if "start" in fv.attrs:
			gr.seq=[]
			key, subStruct=subStructRef(gr.types, fv.attrs["start"])
			try:
				gr = gr.merge(subStruct, {"types"})
			except Exception as ex:
				print("Cannot merge ("+repr(ex)+"), inserting a field: ", key)
				f=KField()
				f.type=key
				f.id=key
				gr.seq.insert(0, f)
		
		if "fileextension" in fv.attrs:
			gr.meta._additional["file-extension"]=fv.attrs["fileextension"].split(",")
			if len(gr.meta._additional["file-extension"]) == 1:
				gr.meta._additional["file-extension"]=gr.meta._additional["file-extension"][0]
		
		if "uti" in fv.attrs:
			gr.meta._additional["-UTI"]=fv.attrs["uti"]
		
		if "author" in fv.attrs or "email" in fv.attrs:
			gr.doc+="\n"
		if "author" in fv.attrs:
			gr.meta._additional["-author"]=fv.attrs["author"]
			gr.doc+=fv.attrs["author"]
			if "email" in fv.attrs:
				gr.doc+=" "
		if "email" in fv.attrs:
			gr.meta._additional["-email"]=fv.attrs["email"]
			gr.doc+="<"+fv.attrs["email"]+">"
		
		if "complete" in fv.attrs:
			gr.meta._additional["-complete"]=fv.attrs["complete"]
		
		
		if not gr.meta.endian:
			gr.meta.endian = "le"
		
		if not gr.meta.encoding:
			gr.meta.encoding="utf-8"
		
		return gr
	
	def structure(converter, fv:bs4.Tag, parentType:KType, self:KType=None) -> KType:
		if self is None:
			self=KType()
		
		self._parent = parentType
		
		#self.meta.endian = getEndianness(fv, None, False) # None and False are intended because parent types endianness is captured automatically by KS from `meta`, no need to repeat
		self.meta.endian = getEndianness(fv, parentType) # don't add None and False to prevent from finding endianness: endianness is used
		
		self.meta.encoding=fv.attrs.get("encoding")
		self.meta._additional["-signed"]=parseBool(fv.attrs.get("signed"))
		
		alignment=fv.attrs.get("alignment")
		if alignment:
			self.meta._additional["-alignment"]=int(alignment) #If a structure must start at a multiple of n bytes, use the alignment field.
		if "consists-of" in fv.attrs:
			self.meta._additional["-consists-of"]=converter.resolveRef(fv.attrs.get("consists-of")) #{name, ref} Select here a parent structure if the structure consists of multiple similar records.
		if "extends" in fv.attrs:
			self.meta._additional["-extends"]=converter.resolveRef(fv.attrs.get("extends")) #{name, ref} Select here the structure to inherit from. Only top-level structures can inherit from other top-level structures
		self.meta._additional["-floating"]=parseBool(fv.attrs.get("floating"))
		
		lengthOffset=fv.attrs.get("lengthoffset")
		if lengthOffset:
			self.meta._additional["-length-offset"]=int(lengthOffset)
		
		self.meta._additional["-order"]=fv.attrs.get("order")  # {'variable', "fixed"} Choose a fixed element order if all elements in the structure have to appear in a fixed order. If only a single element of many is expected, choose variable.
		self.meta._additional["-value-expression"]=fv.attrs.get("valueexpression") # name
		self.meta._additional["-debug"]=parseBool(fv.attrs.get("debug")) # name
		
		if len(fv.contents) == 0:
			newTag=bs4.Tag(name="binary", attrs=fv.attrs)
			
			if "length" not in fv.attrs:
				newTag.attrs["length"]="-1"
			fv.append(newTag)
		
		for field in fv.contents:
			if isinstance(field, bs4.Tag):
				if hasattr(__class__, field.name):
					ctor=getattr(__class__, field.name)
				else:
					raise NotImplementedError("Tag `"+field.name+"` is not implemented!")
				kaitTag=ctor(converter, field, self)
				if kaitTag:
					if not kaitTag.id:
						kaitTag.id=processName(field["name"], self.seq)
					removeOrigIdIfUnneeded(kaitTag, kaitTag.id)
					self.seq.append(kaitTag)
		
		if self:
			typeName=processName(fv["name"], self.types)
			parentType.types[typeName]=self
		
			referer=KField()
			referer.id=typeName
			referer.type=typeName
			converter.processProperty(fv, referer)
			parentType.seq.append(referer)
		
		converter.processGeneric(fv, self)

	def description(converter, fv:bs4.Tag, parentType:KTag):
		parentType.doc=fv.text.strip()
	
	def binary(converter, fv:bs4.Tag, parentType:KType) -> KField:
		"""Binary elements are used for bit or byte sequenced that shouldn't be analyzed in more detail."""
		kaitTag=KField()
		converter.processProperty(fv, kaitTag)
		makeSignatureOrIntEnumIfEnum(converter, fv, parentType, kaitTag, int, enforceSignatureIfSingle=True, endianness="be")
		
		#enumsInThisStruct=fixedvalues(fv, parentType, parentType)
		#if enumsInThisStruct:
		#	return enumsInThisStruct
		
		#kaitTag.size=fv.get("length")
		
		return kaitTag
	
	def structref(converter, fv:bs4.Tag, parentType:KType) -> KField:
		referee=fv.get("structure")
		if not referee:
			referee=transformName(fv["name"])
		else:
			referee=converter.resolveRef(referee)
		
		kaitTag=KField()
		#kaitTag.size=fv["length"]
		kaitTag.type=referee
		converter.processProperty(fv, kaitTag)
		return kaitTag
	
	def offset(converter, fv:bs4.Tag, parentType:KType) -> KInstance:
		#fv["name"]=clearReferenceToPtrFromOffsetName(fv["name"])
		(ptrName, instanceName)=makeAPairOfNamesForPosInstance(fv["name"], parentType)
		
		fv["type"]="integer"
		kaitTag=__class__.number(converter, fv, parentType)
		
		kaitTag.id=ptrName
		removeOrigIdIfUnneeded(kaitTag, kaitTag.id)
		
		inst=KInstance()
		inst.type=converter.resolveRef(fv["references"])
		sz=fv.get("referenced-size")
		if sz:
			inst.size=converter.resolveRef(sz)
			
		inst.pos=kaitTag.id
		
		if 'relative-to' in fv.attrs:
			inst._additional['relative-to']=converter.resolveRef(fv.attrs['relative-to'], name=True)
			inst.pos+=" + lea("+inst._additional['relative-to']+")"
		
		if 'additional' in fv.attrs:
			inst._additional['additional']=converter.parseExpression(fv.attrs['additional'])
			inst.pos+=" + "+str(inst._additional['additional'])
		
		
		fnr=fv.get("follownullreference")
		if fnr:
			fnr=parseBool(fnr)
			if fnr is False:
				boolExprConcat(inst, "if", (kaitTag.id+" != 0"), "and")
			elif(fnr is True):
				pass
			else:
				raise ValueError("unknown value for follownullreference: "+repr(fnr))
		
		parentType.instances[instanceName]=inst
		return kaitTag
	
	def script(converter, fv:bs4.Tag, parentType:KType):
		kaitTag=KField()
		src=fv.select("source")
		converter.processProperty(fv, kaitTag)
		if not src: #oops, source is not parsed because of unknown reason:
			kaitTag._additional["src"]=fv.text
		else:
			kaitTag._additional["src"]=src.text
			kaitTag._additional["language"]=src.get("language")
		parentType._additional["scripts"].append(kaitTag)

	def scripts(converter, fv:bs4.Tag, parentType:KType):
		parentType._additional["scripts"]=[]
		for s in fv.select("script"):
			__class__.script(converter, s, parentType)

	def custom(converter, fv:bs4.Tag, parentType:KType) -> KField:
		"""The script used to parse or translate back to the file is chosen when the custom element is created. The script is copied to the grammar so it doesn't depend on the scripts stored on your disk."""
		kaitTag=KField()
		converter.processProperty(fv, kaitTag)
		kaitTag.process=converter.resolveRef(fv["script"], True)
		return kaitTag
	
	def scriptelement(converter, fv:bs4.Tag, parentType:KType) -> KField:
		__class__.scripts(converter, fv, parentType)
		kaitTag=KField()
		converter.processProperty(fv, kaitTag)
		kaitTag.process=kaitTag.id
		return kaitTag
	
	def grammarref(converter, fv:bs4.Tag, parentType:KType):
		fn=PurePath(fv["filename"]).stem
		#fv["name"]
		#fv["uti"]
		getattr(parentType.meta, "import").append(fn)



originalUFBWXMLTextPropertyName = "-original-ufwb-xml"


class GrammarConverter:
	def __init__(self, grammarFile:typing.Union[_io._IOBase, str, bs4.BeautifulSoup]):
		if isinstance(grammarFile, _io._IOBase):
			grammarFile=grammarFile.read()
		if isinstance(grammarFile, str):
			grammarFile=xmlStr2BS4(grammarFile)
		
		self.registry=Registry(grammarFile)
		self.root=KType()
		self.grammarFile=grammarFile
		self.addXMLForVerification=False
	
	def convert(self):
		for g in self.grammarFile.select("grammar"):
			Processors.grammar(self, g, self.root)
		
		merged=self.root
		parentId=None
		self.root=next(iter(self.root.types.values()))
		
		if "version" in self.grammarFile.attrs:
			self.root.meta._additional["-ufwb-version"]=self.grammarFile.attrs["version"]
		return self.root
	
	def resolveRef(self, mayBeRef:str, hard:bool=False, name=False):
		return self.registry.resolveRef(mayBeRef=mayBeRef, hard=hard, name=name)
	
	
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
	
	
	def processConstraints(self, fv:bs4.Tag, kaitTag:KTag):
		if "repeat" in fv.attrs:
			rm=self.parseExpression(fv.attrs["repeat"])
			kaitTag.repeat="expr"
			kaitTag._additional["repeat-expr"]=rm
			
			boolExprConcat(kaitTag, "-assert", "true", "and")
			if 'minval' in fv.attrs:
				boolExprConcat(kaitTag, "-assert", fv.attrs['repeatmin']+" <= "+rm, "and")
			if 'maxval' in fv.attrs:
				boolExprConcat(kaitTag, "-assert", rm+" <= " +fv.attrs['repeatmax'], "and")
		else:
			if "repeatmin" in fv.attrs: #The minimum repeat count. Parsing fails if that number is not reached.
				rm=self.parseExpression(fv.attrs["repeatmin"])
				if rm:
					kaitTag.repeat="expr"
					kaitTag._additional["repeat-expr"]=rm
					kaitTag._additional["-repeat-min"]=rm
			
			if "repeatmax" in fv.attrs: #The maximum repeat count. Parsing stops if that number is reached.
				rm=fv.attrs["repeatmax"]
				if rm == "unlimited" or rm=="-1": #Select unlimited if the element should fill the remaining space (determined by the enclosing structure).
					kaitTag.repeat="eos"
				else:
					kaitTag._additional["-repeat-max"]=self.parseExpression(rm)

	def processGeneric(self, fv:bs4.Tag, kaitTag:KTag):
		#registry[fv["id"]]=kaitTag
		if "id" in fv.attrs:
			kaitTag._additional["-ufwb-id"]=tryParseInt(fv.attrs["id"])
		
		kaitTag._additional["-orig-id"]=fv.get("name")
		
		if hasattr(kaitTag, "size"):
			if "length" in fv.attrs and kaitTag.size is None:
				l=fv.attrs["length"]
				if l=="remaining" or l=="-1" or l=="0":
					kaitTag._additional["size-eos"]=True
				else:
					kaitTag.size=self.parseExpression(l)

					
		if "fillcolor" in fv.attrs:
			kaitTag._additional["-fill-color"]="#"+fv.attrs["fillcolor"]
		if "strokecolor" in fv.attrs:
			kaitTag._additional["-stroke-color"]="#"+fv.attrs["strokecolor"]
			
		kaitTag._additional["-length-unit"]=fv.attrs.get("lengthunit")
		kaitTag._additional["-must-match"]=fv.attrs.get("mustmatch")
		kaitTag._additional["-disabled"]=parseBool(fv.attrs.get("disabled"))
		kaitTag._additional["-unused"]=parseBool(fv.attrs.get("unused"))
		
		if self.addXMLForVerification:
			kaitTag._additional[originalUFBWXMLTextPropertyName]=str(copyOnlyThisTag(fv))
		
		
		if not kaitTag.doc:
			docTag=fv.select_one("description")
			if docTag:
				Processors.description(self, docTag, kaitTag)
	
	
	def processProperty(self, fv:bs4.Tag, kaitTag:KTag):
		self.processGeneric(fv, kaitTag)
		self.processConstraints(fv, kaitTag)
		if parseBool(fv.attrs.get("disabled")):
			boolExprConcat(kaitTag, "if", "false", "and")
		if parseBool(fv.attrs.get("unused")):
			boolExprConcat(kaitTag, "if", "false", "and")




def grammar2ksy(grammarFile:typing.Union[Path, _io._IOBase, str, bs4.BeautifulSoup], *, addXMLForVerification:bool=False) -> KType:
	if isinstance(grammarFile, Path):
		with grammarFile.open("rt", encoding="utf-8") as f:
			return grammar2ksy(f, addXMLForVerification=addXMLForVerification)
	
	converter=GrammarConverter(grammarFile)
	if addXMLForVerification:
		converter.addXMLForVerification = addXMLForVerification
	return converter.convert()

