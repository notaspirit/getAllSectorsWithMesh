// @description 
// This script is used to find all sectors that contain a specific mesh, it's just cobbled together from another script.
// @usage 
// Make sure archiveContainsStreamingSectors.json is in the resources folder
// Make sure meshCheckSet.json is in the resources folder (and contains the meshes you're looking for)
// Run the script
// @version 0.0.1
// @author spirit


// If you know that the mesh you're looking for is not an entity, set this to true
let skipEntities = true;

const testMode = false;
// max checked sectors
const maxCheckedSectors = 10000000000000000000000;
let checkedSectors = 0;

// Imports 
import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// Global variables
// See sectorExample.txt for template
let bachedJson = [];
let sectorMatches = [];

let meshCheckSet = null;

function getMeshCheckSet() {
    try {
        const meshCheckSetRAW = wkit.LoadFromResources('meshCheckSet.json');
        meshCheckSet = JSON.parse(meshCheckSetRAW);
        Logger.Success('Successfully got meshCheckSet.json');
        // Logger.Info('meshCheckSet.json: ' + JSON.stringify(meshCheckSet[0]));
    } catch (error) {
        Logger.Error('Failed to get meshCheckSet.json: ' + error.message);
    }
}

function getArchiveContainsStreamingSectors() {
    let archiveContainsStreamingSectors = [];
    let cleanedJson = [];
    try {
        const archiveContainsStreamingSectorsRAW = wkit.LoadFromResources('archiveContainsStreamingSectors.json');
        archiveContainsStreamingSectors = JSON.parse(archiveContainsStreamingSectorsRAW);
        Logger.Success('Successfully got archiveContainsStreamingSectors.json');
    } catch (error) {
        Logger.Error('Failed to get archiveContainsStreamingSectors.json: ' + error.message);
    }

    // removes the archiveName from json
    for (let jsonIndex in archiveContainsStreamingSectors) {
        for (let sectorIndex in archiveContainsStreamingSectors[jsonIndex].outputs) {
            cleanedJson.push(archiveContainsStreamingSectors[jsonIndex].outputs[sectorIndex]);
        }
    }
    Logger.Info('Length of cleanedJson: ' + cleanedJson.length);
    // Splits the json into sets of 1000 sectors to process in batches
    const batchSize = 1000;
    for (let i = 0; i < cleanedJson.length; i += batchSize) {
        const batch = cleanedJson.slice(i, i + batchSize);
        bachedJson.push(batch);
}

Logger.Info('Length of bachedJson: ' + bachedJson.length);
}

getArchiveContainsStreamingSectors();
getMeshCheckSet();

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

if (testMode === true) {
    let testSector = 'base\\worlds\\03_night_city\\_compiled\\default\\exterior_0_-34_0_0.streamingsector';
    let testSectorGameFile = wkit.GetFileFromArchive(testSector, OpenAs.GameFile);
    let testSectorData = TypeHelper.JsonParse(wkit.GameFileToJson(testSectorGameFile));
    let nodes = testSectorData["Data"]["RootChunk"]["nodes"];
    let nodeData = testSectorData["Data"]["RootChunk"]["nodeData"]["Data"];

    let matchingNodes = [];
    for (let nodeIndex in nodes) {
        if (getNodeInfo(nodes[nodeIndex], nodeIndex).length > 0) {
            matchingNodes.push(getNodeInfo(nodes[nodeIndex], nodeIndex));
        }
    }
    let nodeIndices = [];
    if (matchingNodes.length > 0) {
        Logger.Info(`Found ${matchingNodes.length} meshes for sector ${testSector}`);
        for (let nodeDataIndex in nodeData) {
            for (let nodeIndex in matchingNodes) {
                if (nodeData[nodeDataIndex]["NodeIndex"] == nodeIndex) {
                    nodeIndices.push(nodeDataIndex);
                }
            }
        }
        sectorMatches.push({sectorName: testSector, nodeIndices: nodeIndices});
    }
    wkit.SaveToResources('testSectorMatches.json', JSON.stringify(sectorMatches, null, 2));
    Logger.Success('Saved testSectorMatches.json');
}



if (testMode === false) {
    // Processes each batch of sectors
    for (let batchIndex in bachedJson) {
        Logger.Info('Processing batch: ' + batchIndex);
        let batchJson = [];
        // Processes each sector in the batch
        for (let sectorIndex in bachedJson[batchIndex]) {
            if (checkedSectors > maxCheckedSectors) {
                Logger.Error('Max checked sectors reached');
                break;
            }
            checkedSectors++;
            let sectorName = bachedJson[batchIndex][sectorIndex].name;
            Logger.Info(`Processing sector: ${sectorName}`);
            let sectorGameFile = wkit.GetFileFromArchive(sectorName, OpenAs.GameFile);
            let sectorData = TypeHelper.JsonParse(wkit.GameFileToJson(sectorGameFile));
            const nodeData = sectorData["Data"]["RootChunk"]["nodeData"]["Data"];
            const nodes = sectorData["Data"]["RootChunk"]["nodes"];

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
    }
    wkit.SaveToResources('SectorMatches.json', JSON.stringify(sectorMatches, null, 2));
    Logger.Success('Saved SectorMatches.json');
}