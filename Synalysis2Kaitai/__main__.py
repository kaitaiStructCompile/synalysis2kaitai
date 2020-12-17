from . import grammar2ksy, originalUFBWXMLTextPropertyName
from plumbum import cli
from tqdm import tqdm as mtqdm
from pathlib import Path

from random import shuffle

class Synalisys2KSYCLI(cli.Application):
	moveDir=cli.SwitchAttr(("S", "moveSuccesfulTo"), cli.switches.MakeDirectory, default="OK", help="The directory to move succesfilly processed files")
	resultsDir=cli.SwitchAttr(("O", "resultsDir"), cli.switches.MakeDirectory, default="results", help="save resuling ksys to this dir")
	moveSuccesful=cli.Flag(("M", "moveSuccesful"), help="move the definitions which processing finished without exceptions reached the level where files are iterated")
	print=cli.Flag(("p", "print"), help="Print resulting ksys into CLI")
	write=cli.Flag(("w", "write"), help="Save resulting ksys")
	sizeOrderedProcessing=cli.Flag(("s", "processInSizeIncreasingOrder"), help="Process small files first. Useful for debugging.")
	addXMLForVerification=cli.Flag(("v", "verificationAssistance"), help="Add XML tags for easier manual verification into `"+originalUFBWXMLTextPropertyName+"` Kaitai attribute. Useful for debugging.")
	failOnException=cli.Flag(("F", "failOnException"), help="fail on an exception")
	
	def main(self, *paths):
		for workingDirOrFile in paths:
			workingDirOrFile=Path(workingDirOrFile)
			if workingDirOrFile.is_dir():
				files=list(workingDirOrFile.glob("*.grammar"))
				#shuffle(files)
				files.sort()
			else:
				files=(workingDirOrFile,)
			
			
			self.resultsDir=Path(self.resultsDir)
			self.resultsDir.mkdir(exist_ok=True)
			
			if self.moveSuccesful:
				self.moveDir=Path(self.moveDir)
				self.moveDir.mkdir(exist_ok=True)
			
			if self.sizeOrderedProcessing:
				files = sorted(files, key=lambda f: f.stat().st_size)
			
		
			with mtqdm(files) as pb:
				for file in pb:
					pb.write(str(file))
					try:
						root=grammar2ksy(file, addXMLForVerification=self.addXMLForVerification)
						if self.print:
							pb.write(str(root))
						if self.write:
							with (self.resultsDir/ (file.stem+".ksy")).open("wt", encoding="utf-8") as f:
								f.write(str(root))
						if self.moveSuccesful:
							file.rename(self.moveDir / file.name)
					except Exception as ex:
						if self.failOnException:
							raise ex
						
						pb.write(str(ex))
					#break

if __name__ == "__main__":
	Synalisys2KSYCLI.run()
