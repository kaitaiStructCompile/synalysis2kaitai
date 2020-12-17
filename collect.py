import sys
import re, _io
from pathlib import Path, PurePath
from functools import lru_cache, partial
from collections import defaultdict

import bs4

import typing


def getThisDir() -> Path:
	try:
		return Path(__file__).parent.absolute()
	except:
		return Path(".").absolute()

thisDir=getThisDir()


from plumbum import cli
from tqdm import tqdm as mtqdm

from random import shuffle
import json
from pprint import pprint

def xmlStr2BS4(s:str) -> bs4.BeautifulSoup:
	"""Converts a string into a BeautifulSoup using the first available parser in the system suitable for us"""
	parsers=("lxml", "xml", "html5lib")
	for p in parsers:
		try:
			return bs4.BeautifulSoup(s, p)
		except:
			pass

class SynalisysGrammarDescr(cli.Application):
	def main(self, workingDir:cli.switches.ExistingDirectory="."):
		workingDir=Path(workingDir)
		
		files=list(workingDir.glob("*.grammar"))
		#shuffle(files)
		files.sort()
		
		res=defaultdict(partial(defaultdict, set))
		queue=[]
		with mtqdm(files) as pb:
			for fileName in pb:
				pb.write(str(fileName))
				with fileName.open("rt", encoding="utf-8") as f:
					if isinstance(f, _io._IOBase):
						f=f.read()
					if isinstance(f, str):
						f=xmlStr2BS4(f)
					if isinstance(f, bs4.Tag):
						queue.append(f)
		
		depth=0
		while queue:
			queueNew=[]
			print(depth, file=sys.stderr)
			for el in queue:
				if not isinstance(el, bs4.Tag):
					continue
				for a in el.attrs:
					res[el.name][a].add(el.attrs[a])
				queueNew.extend(el.children)
			queue=queueNew
			depth+=1
		
		generic=defaultdict(set)
		genericNames={'fillcolor', 'strokecolor', 'id', 'name', 'length', 'lengthunit', 'repeatmax', 'repeatmin'}
		
		for el in res.values():
			for prName in genericNames & el.keys():
				generic[prName]|=el[prName]
				del(el[prName])
		
		res["$generic"]=generic
		pprint(res)
		#print(json.dumps(res))

if __name__ == "__main__":
	SynalisysGrammarDescr.run()
