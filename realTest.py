import ruamel.yaml
from pathlib import Path
import unittest
import enum
from kaitaiStructCompile.specImport import importKSSpec

try:
	thisDir = Path(__file__).parent
except:
	thisDir = Path(".")


realTestsDir = thisDir / "realTests"
testFilesDir = thisDir / "testedFormatsInstances"
convertedSpecsDir = thisDir / "results"
formatsRepoDir = thisDir / "formats"


def getByPath(o, path):
	path = path.split(".")
	for pc in path:
		if isinstance(o, list):
			o = o[pc]
		else:
			o = getattr(o, pc)
	return o

def normalizeValueForComparison(v):
	if isinstance(v, enum.Enum):
		v = v.value
	return v

class RealTest(unittest.TestCase):
	def processIdentitiesDict(self, dic, convertedRoot, nativeRoot):
		for k, v in dic.items():
			self.stepDown(k, v, convertedRoot, nativeRoot)
		
	def stepDown(self, key, value, convertedRoot, nativeRoot):
		if isinstance(value, dict):
			s = key.split("->")
			if len(s) == 1:
				newConvertedRoot = getByPath(convertedRoot, key)
				newNativeRoot = nativeRoot
			elif len(s) == 2:
				newConvertedRoot = getByPath(convertedRoot, s[0].strip())
				newNativeRoot = getByPath(nativeRoot, s[1].strip())
			else:
				raise ValueError("key must be either a path in the converted spec or a par of paths (path in converted spec, path in original spec) separated by `->`")
			self.processIdentitiesDict(value, newConvertedRoot, newNativeRoot)
		elif isinstance(value, str):
			with self.subTest(key=key, value=value):
				convertedV=getByPath(convertedRoot, key)
				nativeV=getByPath(nativeRoot, value)
				self.assertEqual(convertedV, nativeV)
	
	def assertEqual(self, converted, native):
		super().assertEqual(normalizeValueForComparison(converted), normalizeValueForComparison(native))
	
	def doTesting(self, convertedSpecClass, kaitaiNativeSpec, testYaml):
		for fn in testYaml["test_files"]:
			f = testFilesDir / fn
			convertedSpecFile=convertedSpecClass.from_file(str(f))
			kaitaiNativeSpecFile=kaitaiNativeSpec.from_file(str(f))

			self.processIdentitiesDict(testYaml["identities"], convertedSpecFile, kaitaiNativeSpecFile)
	
	
	def testShit(self):
		for testYamlFile in realTestsDir.glob("*.yaml"):
			with self.subTest(yamlFileName = testYamlFile.name):
				yamlRt = ruamel.yaml.YAML(typ="rt")
				testYaml = yamlRt.load(testYamlFile.read_text())
				
				convertedSpec, _ = importKSSpec(convertedSpecsDir / (testYaml["spec_synalysis"]+".ksy"))
				kaitaiNativeSpec, _ = importKSSpec(formatsRepoDir / (testYaml["spec_kaitai"]+".ksy"))
				
				self.doTesting(convertedSpec, kaitaiNativeSpec, testYaml)
	
	@unittest.skip
	def testGif(self):
		yamlRt = ruamel.yaml.YAML(typ="rt")
		testYaml = yamlRt.load((realTestsDir / "gif.yaml").read_text())
		
		from gif_native import Gif as kaitaiNativeSpec
		from gif_converted import Gif as convertedSpec
		self.doTesting(convertedSpec, kaitaiNativeSpec, testYaml)

	@unittest.skip
	def testBmp(self):
		yamlRt = ruamel.yaml.YAML(typ="rt")
		testYaml = yamlRt.load((realTestsDir / "bmp.yaml").read_text())
		
		from bmp_native import Bmp as kaitaiNativeSpec
		from windows_bitmaps_converted import WindowsBitmaps as convertedSpec
		self.doTesting(convertedSpec, kaitaiNativeSpec, testYaml)

	@unittest.skip
	def testZip(self):
		yamlRt = ruamel.yaml.YAML(typ="rt")
		testYaml = yamlRt.load((realTestsDir / "zip.yaml").read_text())
		
		from bmp_native import Bmp as kaitaiNativeSpec
		from windows_bitmaps_converted import WindowsBitmaps as convertedSpec
		self.doTesting(convertedSpec, kaitaiNativeSpec, testYaml)

#FUUUUU

if __name__ == '__main__':
	unittest.main()
