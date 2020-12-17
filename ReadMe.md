Synalysis to Kaitai Struct grammar converter
============================================
[![Code style: antiflash](https://img.shields.io/badge/code%20style-antiflash-FFF.svg)](https://github.com/KOLANICH-tools/antiflash.py)


It's a Work In Progress repo where I store my drafts on implementing https://github.com/kaitai-io/kaitai_struct/issues/383 . For testing it needs some definitions in a working dir, you can get them on https://github.com/synalysis/Grammars/ .

The doc which may be useful for understanding grammars format is by the link: 

Testing workflow
----------------
1. Clone this repo.
2. Go to the working dir (this repo dir assummed).
3. `./scripts/setup.sh`. This will clone the formats repo into a subdir and put differrent sorts of files into subdirs.
4. `./scripts/test.sh` This will try to cmpile the remaining files into KS definitions. Then check the definitions and grammars manually and verify that they correspond to each other. Then add their file names without the last extension into the corresponding file in the lists directory.

Lists description
-----------------

* `not_ok` - it seems there is an error in the definition itself.
* `OK` - compiled into a `ksy` without errors
* `checked_OK` - manual comparison of the `.ksy` and the `.grammar` files showed that it seems that they specify the same grammar (with respect to the tool limitations) AND ksy compiles into python AND python module is IMPORTED succesfully.
* `checked_OK_after_fixes` - error in the definition was manually fixed, after that the same as `checked_OK`.
* `tested_OK` - the resulting `ksy` was tested on actial files
