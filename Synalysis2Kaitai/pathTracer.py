import bs4
from .KSAST import *
from functools import lru_cache
from networkx import DiGraph
from networkx.algorithms import bidirectional_dijkstra, dijkstra_path

idRefRx=re.compile("^id:(.+)$")

def extractUFWBIdFromRef(mayBeRef:str) -> str:
	try:
		id=idRefRx.match(mayBeRef).group(1)
		try:
			id=int(id)
		except:
			pass
		return id
	except:
		return None

class Registry:
	def __init__(self, parsed:bs4.BeautifulSoup):
		self.parsed=parsed

	@lru_cache(256, True)
	def __getitem__(self, id:str):
		#print("registry lookup id", id)
		return transformName(self.parsed.select_one("[id="+str(id)+"]")["name"])
	
	def resolveRef(self, mayBeRef:str, hard:bool=False, name=False):
		id=extractUFWBIdFromRef(mayBeRef)
		if not id:
			if hard or mayBeRef is None:
				raise ValueError(repr(mayBeRef)+" is not a ref")
			if name:
				parts=mayBeRef.split(".")
				if parts[0]=="prev":
					parts=parts[1:]
				elif parts[0]=="this":
					parts=parts[1:]
				print("mayBeRef", mayBeRef)
				mayBeRef=".".join((transformName(p) for p in parts))
			else:
				mayBeRef=transformName(mayBeRef)
			return mayBeRef
		return self[id]


def pathToEdgeData(p, g):
	p = iter(p)
	prevN = next(p)
	for n in p:
		yield g[prevN][n]
		prevN = n

class PathTracer():
	__slots__=("graph",)
	def __init__(self):
		self.graph = DiGraph()
		self.id2Obj = {}
	
	def getID(self, obj)->int:
		return id(obj)
	
	def pathBetweenObjs(self, currentObj, targetObj):
		currentPtr=self.getID(currentObj)
		targetPtr=self.getID(targetObj)
		p = dijkstra_path(self.graph, currentPtr, targetPtr)
		return ".".join(map(lambda x: x["name"], pathToEdgeData(p)))
	
	def addObj(self, obj:typing.Any) -> int:
		nodePtr=self.getID(obj)
		if nodePtr not in self.graph.node:
			self.graph.add_node(nodePtr, {"obj":obj})
	
	def addLink(self, obj:typing.Any, parent:typing.Any, forwardLinkName:str, backwardLinkName:typing.Optional[str]=None):
		nodePtr=self.addObj(obj)
		parentPtr=self.addObj(parent)
		
		self.graph.add_edge(parentPtr, nodePtr, attr_dict={"id": forwardLinkName})
		
		if backwardLinkName is not None:
			self.graph.add_edge(nodePtr, parentPtr, attr_dict={"id": backwardLinkName})
	

class PathTracerUFWB(PathTracer):
	def getID(self, obj)->int:
		return obj.id
	
	def addLink(self, UFWBObj):
		#assert isinstance(UFWBObj, KType)
		super().addLink(UFWBObj, UFWBObj._parent, UFWBObj.name, "_parent")
	
	def resolveRef(self, mayBeRef:str, hard:bool=False, name=False):
		id=extractUFWBIdFromRef(mayBeRef)
		if not id:
			if hard or mayBeRef is None:
				raise ValueError(repr(mayBeRef)+" is not a ref")
			if name:
				parts=mayBeRef.split(".")
				if parts[0]=="prev":
					parts=parts[1:]
				elif parts[0]=="this":
					parts=parts[1:]
				print("mayBeRef", mayBeRef)
				mayBeRef=".".join((transformName(p) for p in parts))
			else:
				mayBeRef=transformName(mayBeRef)
			return mayBeRef
		return self.graph.node[id]["obj"]

class PathTracerKaitai(PathTracer):

	def addLink(self, kaitaiTypeObj:KType):
		assert isinstance(kaitaiTypeObj, KType)
		super().addLink(kaitaiTypeObj, kaitaiObj._parent, kaitaiObj.id, "_parent")
	

class JointPathTracer(PathTracer):
	__slots__=("graph", "kaitaiGraph")
	def __init__(self):
		self.ufwb = PathTracerUFWB()
		self.kaitai = PathTracerKaitai()
		

	def getKaitaiPathFromUFWBRef(self, ufwbRef:str, currentUFWBObj:bs4.Tag, currentKaitaiObj):
		ufwbObj = ufwbObjByUFWBRef(ufwbRef)
		targetKaitaiObj=kaitaiObjFromUFWBObj(ufwbObj)
		return kaitaiPathBetweenObjs(currentKaitaiObj, targetKaitaiObj)
	
	def kaitaiObjFromUFWBObj(self, ufwbObj):
		raise NotImplementedError()
