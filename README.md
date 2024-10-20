# getAllSectorsWithMesh

Little script I wrote for wscript to get all sectors that contain a set of meshes, (optionally also checks entity meshes (this is untested however)).
You will need the list of all sectors and a properly formated json with all the mesh paths you're looking to find. 
It will take a while as it checks all 37k exterior and interior sectors

Both the "meshCheckSet.json" and "archiveContainsStreamingSectors.json" must be in the resources folder of the project you're running this on. 
