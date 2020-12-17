import bs4
import typing
from .KSAST import KType, KField, processName, transformName, DictT
from .utils import *
from .number import *
from functools import partial
import math
import warnings


def makeEnum(valueParser, vals:typing.Iterable[typing.Tuple[str, str]], parentType:KType, id:str=None, enumBitShift=0):
	enum=DictT()
	for k, v in vals:
		v=valueParser(v)
		if enumBitShift:
			v=v>>enumBitShift
		enum[v]=k
	#enum=construct.Enum(construct.Int16ul, **enum)
	if id is None:
		id=len(parentType.enums)
	parentType.enums[id]=enum

processIntEnum=partial(makeEnum, lambda v: int(v, 16))
processSignatureEnum=partial(makeEnum, lambda v: v)

def parseFixedValue(fv:bs4.Tag, tp:type=None, ancestor:bs4.Tag=None) -> typing.Tuple[str, str]:
	name=None
	value=None
	if "name" in fv.attrs:
		name=fv.attrs["name"]
	
	if "value" in fv.attrs:
		value=fv.attrs["value"]
	
	if (value is None or value =="") and fv.text:
		value=fv.text
	
	if tp is int:
		if ancestor and ancestor.name == "binary":
			value=tryParseInt(value, 16)
		else:
			#print(fv, "value", value)
			value=tryParseInt(value)
	
	if not name:
		if isinstance(value, int):
			name="unnamed_"+hex(value)
		else:
			name="unnamed_"+repr(value)
	
	if name:
		name=transformName(name)
	
	return (name, value)

def makeSignature(converter, fv:bs4.Tag, signatureContents:typing.Union[str, typing.Iterable[typing.Union[int, str]]], tp:type, kaitTag=None, endianness=None, parentType=None):
	if kaitTag is None:
		kaitTag=KField()
	if issubclass(tp, str):
		kaitTag.contents=[signatureContents]
	elif issubclass(tp, int):
		sizeDescriptor = getNumberSize(fv)
		l = sizeDescriptor.size
		if sizeDescriptor.isBits:
			l = int(math.ceil(l/8))
			warnings.warn("A number in `"+fv.attrs["name"]+"` must occupy whole bytes, but it doesn't. We have created a ksy anyway, but it won't compile")
		
		if endianness == "dynamic":
			if parentType.meta.endian is None:
				endiannesses2Try=("le", "be")
				synteticFv=[(e, num2EndiannessEncodedBE(signatureContents, l, e)) for e in endiannesses2Try]
				kaitTag.id = processName(fv["name"], parentType.seq)
				enumId = processName(kaitTag.id+"_endianness", parentType.enums)
				
				makeEnumField(fv, synteticFv, tp, parentType, currentKaitTag=kaitTag, sizeDescriptor=sizeDescriptor, enumBitShift=0, endianness="be", enumId=enumId)
				
				parentType.meta.endian={
					"switch-on": kaitTag.id,
					"cases": {enumId+"::"+k: k for k, v in synteticFv}
				}
			else:
				# todo: endian-dependent signature checking
				kaitTag.size = l
			
		else:
			kaitTag.contents = num2array(signatureContents, l, endianness)
	else:
		kaitTag.contents=signatureContents
	converter.processGeneric(fv, kaitTag)
	return kaitTag


def detectFixedValues(fv:bs4.Tag, tp:type, ancestor:bs4.Tag=None) -> typing.List[typing.Tuple[str, str]]:
	detectedFixedValues=[] # (name, value)
	
	fixedValuesTag=None
	fixedValuesTags=[c for c in fv.children if c.name=="fixedvalues"]
	if fixedValuesTags:
		assert len(fixedValuesTags) == 1, "Multiple fixedvalues tags? What is it?"
		fixedValuesTag=fixedValuesTags[0]
	
	if fixedValuesTag:
		fixedValueTagsContainer=fixedValuesTag
	else:
		fixedValueTagsContainer=fv
	
	fixedValueTags=[c for c in fixedValueTagsContainer.children if c.name=="fixedvalue"]
	if fixedValueTags:
		for fixedValueTag in fixedValueTags:
			detectedFixedValues.append(parseFixedValue(fixedValueTag, tp, ancestor))
	elif fixedValuesTag:
		name, value=parseFixedValue(fixedValuesTag, tp, ancestor)
		if name is not None and value is not None:
			detectedFixedValues.append((name, value))
	return detectedFixedValues

def makeEnumField(fv, detectedFixedValues, tp, parentType, currentKaitTag, sizeDescriptor, enumBitShift:int=0, endianness=None, enumId:str=None):
	if enumId is None:
		enumId = currentKaitTag.id
	processSignatureEnum(detectedFixedValues, parentType, enumId, enumBitShift=enumBitShift) #KS doesn't support multiple signatures, we need to have 2 types of enums, mustMatch=True and mustMatch=False
	currentKaitTag.enum=enumId
	if tp is int:
		currentKaitTag.type=getNumberType(fv, sizeDescriptor, endianness, parentType=parentType)

def makeSignatureOrIntEnumIfEnum(converter, fv:bs4.Tag, parentType:KType, currentKaitTag, tp:type, enforceSignatureIfSingle:bool=False, sizeDescriptor=None, enumBitShift:int=0, endianness:typing.Optional[str]=None) -> bool:
	"""Checks if current member is a enum, if it is, creates a enum and returns True, otherwise returns False"""
	currentKaitTag.id=processName(fv["name"], parentType.seq)
	detectedFixedValues=detectFixedValues(fv, tp, fv)
	#print("detectedFixedValues", detectedFixedValues)
	if detectedFixedValues:
		currentKaitTag.size=None
		if len(detectedFixedValues) == 1 and (parseBool(fv.attrs.get("mustmatch")) or enforceSignatureIfSingle):
			# it's a signature
			k, v=detectedFixedValues[0]
			currentKaitTag=makeSignature(converter, fv, signatureContents=v, tp=tp, kaitTag=currentKaitTag, endianness=endianness, parentType=parentType)
		else:
			makeEnumField(fv, detectedFixedValues, tp, parentType, currentKaitTag, sizeDescriptor, enumBitShift=enumBitShift, endianness=endianness)
		return True
	else:
		return False
