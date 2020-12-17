source ${BASH_SOURCE%/*}/config.sh

mv $OK_DIR/*.grammar $SYNALYSIS_REPO_DIR
python3 -m Synalysis2Kaitai --verificationAssistance --processInSizeIncreasingOrder --write --moveSuccesful --moveSuccesfulTo $OK_DIR -F $SYNALYSIS_REPO_DIR