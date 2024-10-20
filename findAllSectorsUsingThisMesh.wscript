// @description 
// This script is used to find all sectors that contain a specific mesh, it's just cobbled together from another script.
// @usage 
// Make sure archiveContainsStreamingSectors.json is in the resources folder
// Make sure meshCheckSet.json is in the resources folder (and contains the meshes you're looking for)
// Run the script
// @version 0.0.3
// @author spirit


// If you know that the mesh you're looking for is not an entity, set this to true
// WARNING: This is untested, so keep it true
let skipEntities = true;

// Imports 
import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// Global variables
// See sectorExample.txt for template
let sectorMatches = [];
let failedSectors = [];

let meshCheckSet = null;
let settings = null;
const batchSize = 1000;

let defaultSettings = {batchSize: batchSize, totalBatches: 0, lastBatch: 0};


/*
Conceptually what we need to do here is:
check if the list of streaming sectors is already batched (with the correct batch size)
if there are batches but they are not the correct size, we error out
if there are no batches, we batch the sectors and exit
if there are batches and they are the correct size, we continue
we check if the batch is already processed, if it is we skip it
if it is not, we process it and exit after

would be very nice if we don't have to load the entire json with the list of streaming sectors into memory
will need to restructure it for that so that a different json contains the length and current progress


folder structure for the resources folder:
resources/
├─ GSFM/
│  ├─ input/
│  │  ├─ meshCheckSet.json
│  │  ├─ archiveContainsStreamingSectors.json
│  ├─ settings.json 
│  ├─ batchedSectors/
│  ├─ output/

If formatted properly e.g. using / instead of \ for the folder structure "SaveToResources" can handle creating the folders
*/

// Functions
// Extracts Mesh and Transform data from component List
function getMeshSetFromComponents(components) {
    let localMeshGroup = [];
    for (let component of components) {
        if (component.$type.includes("Mesh")) {
            let localTransform = component.localTransform;
            let posRAW = [];
            posRAW.push({x: localTransform.Position.x, y: localTransform.Position.y, z: localTransform.Position.z});
            let meshPath = component.mesh.DepotPath.value;

            let posX = decodeFixedPoint(posRAW[0].x.Bits, 16);
            let posY = decodeFixedPoint(posRAW[0].y.Bits, 16);
            let posZ = decodeFixedPoint(posRAW[0].z.Bits, 16);

            let qi = localTransform.Orientation.i;
            let qj = localTransform.Orientation.j;
            let qk = localTransform.Orientation.k;
            let qr = localTransform.Orientation.r;
            Logger.Success(`Found mesh path: ${meshPath}`);

            localMeshGroup.push({
                meshPath: meshPath,
                quat: { i: qi, j: qj, k: qk, r: qr }, // Use curly braces for objects
                pos: { x: posX, y: posY, z: posZ }    // Use curly braces for objects
            });
        }
    }
    return localMeshGroup;
}


// gets mesh path from ent path and appearance
function getMeshPath(entPath, appearanceInput) {
    let entGameFile = wkit.GetFileFromArchive(entPath, OpenAs.GameFile);
    let entData = TypeHelper.JsonParse(wkit.GameFileToJson(entGameFile));
    let meshGroup = [];
    if (appearanceInput === 'default') {
        // Here you can get the mesh directly from the ent under "components"
        let components = entData.Data.RootChunk.components;
        meshGroup.push(...getMeshSetFromComponents(components));
    } else {
        // Here you have to get the mesh from the .app file
        // IMPORTANT:
        // The appearance name in the .app file isn't the same as in the node, it can be found under "appearanceName" in the .ent
        Logger.Info("Entity Has complex appearance: " + entPath + " " + appearanceInput);
        let appearances = entData.Data.RootChunk.appearances;
        let shortAppearanceName = '';
        let appearanceResource = '';
        for (let appearance of appearances) {
            if (appearance.name == appearanceInput) {
                shortAppearanceName = appearance.appearanceName;
                appearanceResource = appearance.appearanceResource.DepotPath.value;
                break;
            }
        }
        Logger.Info(`Short appearance name: ${shortAppearanceName}`);
        Logger.Info(`Appearance resource: ${appearanceResource}`);
        let appearanceData = null;
        try {
            let appearanceGameFile = wkit.GetFileFromArchive(appearanceResource, OpenAs.GameFile);
            appearanceData = TypeHelper.JsonParse(wkit.GameFileToJson(appearanceGameFile));
        } catch (error) {
            Logger.Error(`Failed to get appearance data for ${entPath} ${appearanceInput}: ${error.message}`);
        }
        let appAppearances = appearanceData.Data.RootChunk.appearances;
        for (let appAppearance of appAppearances) {
            if (appAppearance.Data.name.value == shortAppearanceName) {
                Logger.Success(`Found appearance: ${appAppearance.Data.name.value}`);
                let components = appAppearance.Data.components;
                meshGroup.push(...getMeshSetFromComponents(components));
                break;
            }
        }
    }

    return meshGroup;
}

// Gets all relevant node info out of "node"
function getNodeInfo(nodeInstance, nodeIndex) {
    let foundMesh = []
    Logger.Info(`Checking Node ${nodeIndex} for mesh`);
    // Getting the mesh only path works and is done
    try {
        const depoPathMeshJS = nodeInstance["Data"]["mesh"]["DepotPath"];
        for (let key in depoPathMeshJS) {
            if (key.includes("value")) {
                if (meshCheckSet.includes(depoPathMeshJS[key])) {
                    foundMesh.push(depoPathMeshJS[key]);
                }
            }
        }
    } catch (error) {
    }
    // Getting the meshes from an entity template works and is done
    if (skipEntities === false) {
        try {
            let entPath = '';
        let entAppearance = '';
        const depoPathEntJS = nodeInstance["Data"]["entityTemplate"]["DepotPath"];
        const depoPathAppearanceJS = nodeInstance["Data"]["appearanceName"];
        for (let key in depoPathEntJS) {
            if (key.includes("value")) {
                entPath = depoPathEntJS[key];
            }
        }
        for (let key in depoPathAppearanceJS) {
            if (key.includes("value")) {
                entAppearance = depoPathAppearanceJS[key];
            }
        }
        if (entPath !== '' && entAppearance !== '') {
            for (let mesh of getMeshPath(entPath, entAppearance)) {
                if (meshCheckSet.includes(mesh.meshPath)) {
                    foundMesh.push(mesh);
                }
            }
        }
        if ((entPath !== '' && entAppearance === '') || (entPath === '' && entAppearance !== '')) {
            Logger.Error(`Node ${nodeIndex} has an invalid entity template or appearance: ${entPath} ${entAppearance}`);
            }
        } catch (error) {
        }
    }
    if (foundMesh.length > 0) {
        Logger.Success(`Found ${foundMesh.length} meshes for node ${nodeIndex}`);
        return foundMesh;
    }
    Logger.Info(`No meshes found for node ${nodeIndex}`);
    return [];
}

function processBatch(batchJson) {
    // Processes each sector in the batch
    for (let sectorIndex in batchJson) {
        let sectorName = batchJson[sectorIndex].name;
        Logger.Info(`Processing sector: ${sectorName} (${sectorIndex}/${batchJson.length})`);
        let sectorGameFile = null;
        let sectorData = null;
        let nodeData = null;
        let nodes = null;
        try {
            sectorGameFile = wkit.GetFileFromArchive(sectorName, OpenAs.GameFile);
            sectorData = TypeHelper.JsonParse(wkit.GameFileToJson(sectorGameFile));
            nodeData = sectorData["Data"]["RootChunk"]["nodeData"]["Data"];
            nodes = sectorData["Data"]["RootChunk"]["nodes"];
        } catch (error) {
            failedSectors.push(sectorName);
            Logger.Error(`Failed to get sector data for ${sectorName}: ${error}`);
            continue;
        }
        let matchingNodes = [];
        for (let nodeIndex in nodes) {
            if (getNodeInfo(nodes[nodeIndex], nodeIndex).length > 0) {
                matchingNodes.push(getNodeInfo(nodes[nodeIndex], nodeIndex));
            }
        }
        let nodeDataIndices = [];
        if (matchingNodes.length > 0) {
            Logger.Info(`Found ${matchingNodes.length} meshes for sector ${sectorName}`);
            for (let nodeDataIndex in nodeData) {
                for (let nodeIndex in matchingNodes) {
                    if (nodeData[nodeDataIndex]["NodeIndex"] == nodeIndex) {
                        nodeDataIndices.push(nodeDataIndex);
                    }
                }
            }
            sectorMatches.push({sectorName: sectorName, nodeDataIndices: nodeDataIndices});
        }
    }
    return sectorMatches;
}




// Logic thing
try {
    let meshCheckSetRAW = wkit.LoadFromResources('GSFM/input/meshCheckSet.json');
    meshCheckSet = JSON.parse(meshCheckSetRAW);
    let testValue = meshCheckSet[0];
    Logger.Success(`GSFM/input/meshCheckSet.json exists`);
} catch (error) {
    Logger.Error(`GSFM/input/meshCheckSet.json does not exist`);
    Logger.Error(`Error: ${error}`);
}

try {
    let settingsRaw = wkit.LoadFromResources('GSFM/settings.json');
    settings = JSON.parse(settingsRaw);
    let settingsTest = settings.batchSize;
    Logger.Success(`GSFM/settings.json exists`);
} catch (error) {
    wkit.SaveToResources('GSFM/settings.json', JSON.stringify(defaultSettings, null, 2));
    let settingsRaw = wkit.LoadFromResources('GSFM/settings.json');
    settings = JSON.parse(settingsRaw);
    Logger.Success(`GSFM/settings.json created`);
}

if (settings.batchSize !== batchSize) {
    Logger.Error(`Batch size in settings.json is not equal to the current batch size, adjust batch size or clear current progress`);
}
if (settings.totalBatches === 0) {
    Logger.Info(`No batches found, creating batches`);
    let archiveContainsStreamingSectors = [];
    let cleanedJson = [];
    try {
        const archiveContainsStreamingSectorsRAW = wkit.LoadFromResources('GSFM/input/archiveContainsStreamingSectors.json');
        archiveContainsStreamingSectors = JSON.parse(archiveContainsStreamingSectorsRAW);
        if (archiveContainsStreamingSectors.length > 0) {
            Logger.Success('Successfully got archiveContainsStreamingSectors.json');
        } else {
            Logger.Error('archiveContainsStreamingSectors.json is empty');
        }
    } catch (error) {
        Logger.Error('Failed to get archiveContainsStreamingSectors.json from resources');
    }

    // removes the archiveName from json
    for (let jsonIndex in archiveContainsStreamingSectors) {
        for (let sectorIndex in archiveContainsStreamingSectors[jsonIndex].outputs) {
            cleanedJson.push(archiveContainsStreamingSectors[jsonIndex].outputs[sectorIndex]);
        }
    }
    Logger.Info(`Total Sectors: ${cleanedJson.length}`);
    // Splits the json into sets of 1000 sectors to process in batches
    let batchIndex = 1;
    for (let i = 0; i < cleanedJson.length; i += batchSize) {
        const batch = cleanedJson.slice(i, i + batchSize);
        wkit.SaveToResources(`GSFM/batchedSectors/batch${batchIndex}.json`, JSON.stringify(batch, null, 2));
        batchIndex++;
    }
    settings.totalBatches = batchIndex;
    wkit.SaveToResources('GSFM/settings.json', JSON.stringify(settings, null, 2));
    Logger.Success(`GSFM/settings.json updated`);
    Logger.Info(`Total batches: ${settings.totalBatches}`);
    Logger.Info(`To start processing batches run script again`);
} else if (settings.lastBatch < settings.totalBatches) {
    Logger.Info(`Batches already exist, starting next batch: ${settings.lastBatch + 1}/${settings.totalBatches}`);
    let batchJsonRAW = wkit.LoadFromResources(`GSFM/batchedSectors/batch${settings.lastBatch + 1}.json`);
    let batchJson = JSON.parse(batchJsonRAW);
    let sectorMatchesOutput = processBatch(batchJson);
    settings.lastBatch++;
    wkit.SaveToResources('GSFM/settings.json', JSON.stringify(settings, null, 2));
    Logger.Success(`GSFM/settings.json updated`);
    wkit.SaveToResources(`GSFM/output/batch${settings.lastBatch}.json`, JSON.stringify(sectorMatchesOutput, null, 2));
    Logger.Success(`GSFM/output/batch${settings.lastBatch}.json saved`);
    Logger.Info('For better stability, clear wolvenkit logs');
    Logger.Info(`To continue processing batches run script again`);
    if (failedSectors.length > 0) {
        Logger.Info(`Failed to process ${failedSectors.length} sectors`);
        wkit.SaveToResources(`GSFM/output/failedSectors${settings.lastBatch}.json`, JSON.stringify(failedSectors, null, 2));
        Logger.Success(`GSFM/output/failedSectors${settings.lastBatch}.json saved`);
    }
} else {
    Logger.Info(`All batches processed, merging results`);
    let finalOutput = [];
    for (let batchIndex in settings.output) {
        let batchOutputRAW = wkit.LoadFromResources(`GSFM/output/batch${batchIndex}.json`);
        let batchOutput = JSON.parse(batchOutputRAW);
        finalOutput.push(...batchOutput);
    }
    wkit.SaveToResources('GSFM/output/finalOutput.json', JSON.stringify(finalOutput, null, 2));
    Logger.Success('GSFM/output/finalOutput.json saved');
}
