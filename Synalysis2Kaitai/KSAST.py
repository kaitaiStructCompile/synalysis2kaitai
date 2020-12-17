__author__="KOLANICH"
__license__="Unlicense"

import typing
import re
from io import StringIO
from functools import partial
from pprint import pprint

from collections import OrderedDict
import ruamel.yaml


yamlDumper = ruamel.yaml.YAML(typ="rt")
yamlDumper.indent(mapping=2, sequence=4, offset=2)

def yaml(o) -> str:
	with StringIO() as s:
		yamlDumper.dump(o, s)
		return s.getvalue()

class Mergeable:
	"""A class meaning that an a merge operation is implemented for class inheriting it"""
	def merge(self, another):
		raise NotImplementedError("Merge operation should be implemented for the class "+self.__class__.__name__+" but it is not")

class MergeableCollection(Mergeable):
	"""A class providing a facility to merge subentities. Merging procedure should be implemented manually."""
	def mergePairOfItems(grA:Mergeable, stA:Mergeable, allowConflict:bool, key=None):
		if not grA and stA:
			return stA
		elif not stA and grA:
			return grA
		elif stA is grA:
			return grA
		elif not stA and not grA:
			return grA
		elif isinstance(grA, Mergeable):
			return grA.merge(stA)
		#elif isinstance(stA, Mergeable):
		#	return stA.merge(grA)
		#elif isinstance(stA, (dict, OrderedDict)) and isinstance(grA, (dict, OrderedDict)):
		#	return DictT(grA).merge(stA)
		elif isinstance(stA, (list, tuple)) and isinstance(grA, (list, tuple)):
			return ListT(grA).merge(stA)
		elif allowConflict:
			return stA
		else:
			#print("Not merged, props conflict", key, grA, stA)
			raise Exception("Not merged, props conflict", key, grA, stA)
			
	
	def mergeIter(self, another):
		raise NotImplementedError("Merge iter operation should be implemented for the class "+self.__class__.__name__+" but it is not")
	
	def mergeSetter(self, res, k, v):
		raise NotImplementedError("Merge setter should be implemented for the class "+self.__class__.__name__+" but it is not")
	
	def merge(self, another, *args, **kwargs):
		res=self.__class__()
		for (a, b, allowConflict, key) in self.mergeIter(another, *args, **kwargs):
			self.mergeSetter(res, key, self.__class__.mergePairOfItems(a, b, allowConflict, key))
		return res


@ruamel.yaml.yaml_object(yamlDumper)
class DictT(OrderedDict, MergeableCollection):
	@classmethod
	def to_yaml(cls:type, representer, node):
		return representer.represent_dict(node)
	
	def mergeSetter(self, res, k, v):
		res[k]=v
	
	def mergeIter(self, another, allowConflicts:set=frozenset()):
		for k in self.keys()|another.keys():
			yield (self.get(k), another.get(k), k in allowConflicts, k)


@ruamel.yaml.yaml_object(yamlDumper)
class ListT(list, MergeableCollection):
	@classmethod
	def to_yaml(cls:type, representer, node):
		return representer.represent_list(node)
	
	def mergeSetter(self, res, k, v):
		res[k]=v
	
	def mergeIter(self, another, allowConflicts:typing.Set[int]=frozenset()):
		for k in range(max(len(self), len(another))):
			a=self[k] if k<len(self) else None
			b=another[k] if k<len(another) else None
			yield (a, b, k in allowConflicts, k)


@ruamel.yaml.yaml_object(yamlDumper)
class NamespaceDict(DictT, Mergeable):
	__slots__=("_namespace",)
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._namespace=set()


num2wordsDic={
	'0':"zero",
	'1':"one",
	'2':"two",
	'3':"three",
	'4':"four",
	'5':"five",
	'6':"six",
	'7':"seven",
	'8':"eight",
	'9':"nine"
}
def strNum2NumWords(n:str):
	return "_".join((num2wordsDic[c] for c in n))


capRx=re.compile("(?<=[a-z])([A-Z]+)(?=>[a-z]|$)|([A-Z][a-z]+)|_|\\s+")
forbiddenCharsRx=re.compile("[^a-zA-Z0-9_]")
whitespaceCharsRx=re.compile("\\s")
leadingNumberRx=re.compile("^\\d+")

import unicodedata
unicodeNameStopList = {"sign", "greek", "latin", "capital" ,"letter", "small", "digit", "mark", "accent"}

def transformForbiddenChar(c):
	nm=unicodedata.name(c.group(0)).lower()
	nm=(w for w in nm.split(" ") if w not in unicodeNameStopList)
	r = "_".join(nm)
	return r

def transformName(name:str) -> str:
	name=unicodedata.normalize("NFKD", name)
	name=leadingNumberRx.sub(lambda n: strNum2NumWords(n.group(0))+"_", name)
	name, n=whitespaceCharsRx.subn("_", name)
	name, n=forbiddenCharsRx.subn(transformForbiddenChar, name)
	name="_".join(( g for g in capRx.split(name) if g))
	return name.lower()

ruamel.yaml.representer.SafeRepresenter.add_representer(OrderedDict, ruamel.yaml.representer.SafeRepresenter.represent_dict)


@ruamel.yaml.yaml_object(yamlDumper)
class KaitOrdEnt(MergeableCollection):
	"""A base class providing some facilities for dumping its contents as "dumb" YAML preserving the order"""
	__slots__=("_additional",)
	
	def __init__(self):
		for cls in self.__class__.mro():
			if cls is __class__:
				break
			for k in cls.__slots__:
				setattr(self, k, None)
		self._additional=DictT()
	
	def __str__(self):
		return yaml(self)
	
	def __repr__(self):
		return str(self)
		sio=StringIO()
		pprint(self.represent(), sio)
		return sio.getvalue()
	
	def __bool__(self):
		return any((getattr(self, k) for k in self.__class__.__slots__))
	
	
	def __contains__(self, k):
		return hasattr(self, k) or k in self._additional
	
	def __getitem__(self, k):
		if hasattr(self, k):
			return getattr(self, k)
		else:
			return self._additional.get(k)
	
	def __setitem__(self, k, v):
		if hasattr(self, k):
			setattr(self, k, v)
		else:
			self._additional[k]=v
	
	def genRepr(cls:type, self, r:dict):
		for k in cls.__slots__:
			if k[0]=="_":
				continue
			v=getattr(self, k)
			if v:
				#most of the following shit is for simple YAML
				if isinstance(v, str):
					if "\n" in v:
						v=ruamel.yaml.representer.PreservedScalarString(v)
				r[k]=v
	
	def represent(self) -> dict:
		r=DictT()
		for cls in self.__class__.mro():
			if cls is __class__:
				break
			self.__class__.genRepr(cls, self, r)
		r.update(
			type(self._additional)(
				( (k,v) for k,v in self._additional.items() if v )
			)
		)
		return r
	
	@classmethod
	def to_yaml(cls:type, representer, node):
		return representer.represent_dict(node.represent())
	
	def mergeSetter(self, res, k, v):
		setattr(res, k, v)
	
	def mergeIter(self, another, allowConflicts:typing.Set[str]=frozenset()):
		for cls in self.__class__.mro():
			if cls is __class__:
				break
			for s in cls.__slots__:
				if s[0]=="_":
					continue
				yield (getattr(self, s), getattr(another, s), s in allowConflicts, s)
		yield (self._additional, another._additional, True, "_additional")

@ruamel.yaml.yaml_object(yamlDumper)
class KTag(KaitOrdEnt):
	__slots__=("doc", "_parent")
	def __init__(self):
		super().__init__()


@ruamel.yaml.yaml_object(yamlDumper)
class KMeta(KaitOrdEnt):
	__slots__=("id", "title", "endian", "encoding", "import")
	def __init__(self):
		super().__init__()
		setattr(self, "import", [])

@ruamel.yaml.yaml_object(yamlDumper)
class KType(KTag):
	__slots__=("meta", "doc", "seq", "instances", "types", "enums")
	def __init__(self):
		super().__init__()
		self.meta=KMeta()
		self.doc=""
		self.seq=[]
		self.instances={}
		self.types={}
		self.enums={}
	
	@property
	def endianness(self):
		"""Used to retrieve endianness of this type"""
		if self.meta.endian is not None:
			return self.meta.endian
		if self._parent is not None:
			return self._parent.endianness
	
	@endianness.setter
	def endianness(self, v):
		if self.endianness != v:
			self.meta.endian = v

	@property
	def encoding(self):
		"""Used to retrieve encoding of this type"""
		if self.meta.encoding is not None:
			return self.meta.encoding
		if self._parent is not None:
			return self._parent.encoding
	
	@endianness.setter
	def encoding(self, v):
		if self.encoding != v:
			self.meta.encoding = v
	
	def processName(self, name:str) -> str:
		return processName(name, self)
	
	
	@property
	def id(self):
		return self.meta.id
	
	@id.setter
	def id(self, v):
		self.meta.id=v
	
	def merge(self, another, *args, **kwargs):
		return super().merge(another, *args, **kwargs)

def processName(name:str, parentType:KType):
	return transformName(name)

@ruamel.yaml.yaml_object(yamlDumper)
class KField(KTag):
	__slots__=("id", "type", "enum", "size", "contents", "if", "encoding", "process", "repeat")
	def __init__(self):
		super().__init__()

@ruamel.yaml.yaml_object(yamlDumper)
class KInstance(KField):
	__slots__=("pos", "value", "io")
	def __init__(self):
		super().__init__()

