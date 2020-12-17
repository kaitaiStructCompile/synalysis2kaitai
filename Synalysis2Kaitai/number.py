import bs4
from .utils import *
from .KSAST import KType

endiannessNameRemapping={
	"big": "be",
	"little": "le",
	"dynamic": "dynamic" # todo: determining endianness?
}

numberTypeMapping={
	"integer": "u",
	"float": "f",
}
bitsInAByte=8

class NumberSizeDescriptor():
	__slots__=("size", "isBits")
	def __init__(self, size:int, isBits:bool):
		self.size=size
		self.isBits=isBits

def getEndianness(fv:bs4.Tag, parentType:typing.Optional[KType]=None, searchXMLHierarchy:bool=True, defaultEndianness:typing.Optional[str]=None) -> str:
	end = None
	if "endian" in fv.attrs:
		end = endiannessNameRemapping[fv.attrs["endian"]]
	
	if end is None and isinstance(parentType, KType):
		end = parentType.endianness
	
	if end is None and searchXMLHierarchy and fv.parent and fv.parent is not fv:
		#print(copyOnlyThisTag(fv.parent))
		end = getEndianness(fv.parent, None, searchXMLHierarchy)
	
	if end is None:
		end = defaultEndianness
		#raise Exception("Cannot find endianness")
	
	return end


def getNumberSize(fv:bs4.Tag, bits:bool=False) -> NumberSizeDescriptor:
	isBits=False
	l=None
	if "length" in fv.attrs:
		l=tryParseInt(fv.attrs["length"])
	
	if fv.attrs.get("lengthunit") == "bit":
		return NumberSizeDescriptor(l, True)
	else:
		if "length" not in fv.attrs:
			l=4 # my assumption, may be wrong
		if bits:
			l*=bitsInAByte
		return NumberSizeDescriptor(l, bits)

def getNumberType(fv:bs4.Tag, sizeDescriptor:NumberSizeDescriptor=None, endianness:typing.Optional[str]=None, parentType=None):
	if "type" not in fv.attrs:
		fv.attrs["type"]="integer" # my assumption, may be wrong
	tp=numberTypeMapping[fv.attrs["type"]]
	
	if parseBool(fv.attrs.get("signed")) and tp is "u":
		tp="s"
	
	if sizeDescriptor is None:
		sizeDescriptor=getNumberSize(fv)
	
		
	if tp[0] != "f":
		if endianness is None:
			end=getEndianness(fv, parentType, sizeDescriptor.isBits)
		else:
			end=endianness
	else:
		end=""
	
	if sizeDescriptor.isBits:
		assert (tp[0] == "u"), "Non-Uint bit-sized types are not supported yet"
		assert (not end or end == "be"), "Non BE bit-sized types are not supported yet"
		res="b"+str(sizeDescriptor.size)
	else:
		if "length" in fv.attrs:
			del(fv.attrs["length"]) # to prevent creation of this prop in ksy, it is not allowed for numbers
		res=tp+str(sizeDescriptor.size)
		if sizeDescriptor.size > 1 and "endian" in fv.attrs and fv.attrs["endian"] != end:
			res+=end
	return res
