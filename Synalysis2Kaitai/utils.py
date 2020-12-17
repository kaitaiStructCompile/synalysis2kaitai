import re

import bs4

import typing
import warnings

class _RangeToMasker:
	def __getitem__(self, r):
		if isinstance(r, int):
			return 1 << r
		else:
			r = snormalize(r)
			return 2**slen(r)-1 << r.start
	
	def __call__(self, r):
		return self[r]

range2mask = _RangeToMasker()

from rangeslicetools import slen, snormalize
from Endianness import Endianness, EndiannessMapping, wellKnown


def num2EndiannessEncodedBE(num:int, byteLength, endianness:typing.Optional[typing.Union[str, Endianness]]=None) -> int:
	"""
	num - is a number in machine-format
	
	returns a number, which when encoded as big-endian gives bytes equivalent to that number encoded in desired encoding
	"""
	
	bitLength = byteLength * 8
	if endianness is None:
		endianness = "le"
		warnings.warn("Unknown endianness for a signature. Assumming `"+endianness+"`")
	if isinstance(endianness, str):
		endianness=wellKnown[endianness]
	
	
	m = EndiannessMapping(endianness, bitLength)
	encoded = list(m.encode(slice(bitLength,-1, -1)))
	del m
	
	res = 0
	for n in encoded:
		#print(n)
		m = range2mask[n.index]
		#print(hex(m))
		maskStart = snormalize(n.index).start
		
		part = ((num & m) >> maskStart) << snormalize(n.indexee).start
		#print(part)
		res |= part
	
	return res

def num2array(num:int, byteLength, endianness:typing.Optional[typing.Union[str, Endianness]]=None):
	return list(num2EndiannessEncodedBE(num, byteLength, endianness=endianness).to_bytes(byteLength, "big", signed=False))

#def num2array(num:int, byteLength, endianness:str):
#	res=[0]*byteLength
#	for i in range(byteLength):
#		res[i]=num&0xff
#		num=num>>8
#	if be:
#		res.reverse()
#	return res


unclosedXmlElementRx=re.compile("<(\\w+)(\\s+[^>]+)?/>")
def xml2html(t):
	return unclosedXmlElementRx.subn("<\\1\\2></\\1>", t)[0]

def copyOnlyThisTag(tg:bs4.Tag):
	return bs4.Tag(name=tg.name, attrs=tg.attrs)

def xmlStr2BS4(s:str) -> bs4.BeautifulSoup:
	"""Converts a string into a BeautifulSoup using the first available parser in the system suitable for us"""
	parsers=("lxml", "xml", "html5lib")
	for p in parsers:
		try:
			if p == "html5lib":
				s1=xml2html(s)
				return bs4.BeautifulSoup(s1, p)
			return bs4.BeautifulSoup(s, p)
		except Exception as ex:
			#print(ex)
			pass


def tryParseInt(inp:str, base:int=10) -> typing.Union[int, str]:
	if inp[0:2]=="0x":
		base=16
	try:
		return int(inp, base)
	except:
		return inp

def parseBool(val:str) -> bool:
	if val == "yes":
		return True
	elif val == "no":
		return False
	else:
		return None

def cleanLastMatchFromStr(rx, s:str) -> str:
	r=rx.split(s)
	if len(r) >=2:
		r[-2]=""
	return "".join(r)


def maskToBitRangesIter(mask:int) -> slice:
	print(hex(mask), bin(mask))
	if not mask:
		raise ValueError("mask must be greater than 0")
	start=0
	#we should really use popcnt x86 instr from python
	while mask:
		while not mask&1:
			mask=mask>>1
			start+=1
		end=start
		while mask&1:
			mask=mask>>1
			end+=1
		yield slice(start, end)

def maskToBitRanges(mask:int) -> typing.List[slice]:
	return list(maskToBitRangesIter(mask))
