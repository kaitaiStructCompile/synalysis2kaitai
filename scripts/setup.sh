source ${BASH_SOURCE%/*}/config.sh

mkdir $GRAMMARS_DIRS

git clone $SYNALYSIS_REPO $SYNALYSIS_REPO_DIR
for listFileName in ./lists/*.txt; do
	foldName=$(basename $listFileName | sed -E -e "s/(.*)\.txt/\1/")
	echo $foldName;
	mkdir $GRAMMARS_DIRS/$foldName;
	for fileName in $(cat $listFileName); do
		mv $SYNALYSIS_REPO_DIR/$fileName.grammar $GRAMMARS_DIRS/$foldName;
	done;
done;