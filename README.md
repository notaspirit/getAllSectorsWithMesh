# getAllSectorsWithMesh

Little script I wrote for wscript to get all sectors that contain a set of meshes, (optionally also checks entity meshes (this is untested however)).
You will need the list of all sectors and a properly formated json with all the mesh paths you're looking to find. 
It will take a while as it checks all 37k exterior and interior sectors

script goes into %AppData%\REDModding\WolvenKit\WScript

!! IMPORTANT:
in 0.0.3-alpha the folder structure within the project resources folder changed!
New structure:

resources/

├─ GSFM/

│  ├─ input/

│  │  ├─ meshCheckSet.json

│  │  ├─ archiveContainsStreamingSectors.json

│  ├─ settings.json 

│  ├─ batchedSectors/

│  ├─ output/

To start from scratch delete everything in the GSFM folder except the input folder!
