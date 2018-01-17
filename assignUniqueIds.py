from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QInputDialog
import itertools
import time

def getSidewalkLayer():
    sidewalkLayerName = "sidewalks"
    sidewalkLayerList = (
        QgsMapLayerRegistry.instance()
        .mapLayersByName(sidewalkLayerName)
    )
    if sidewalkLayerList:
        sidewalkLayer = sidewalkLayerList[0]
    return sidewalkLayer


def assignUniqueIdsToSidewalks():
    sidewalkLayer = getSidewalkLayer()
    createUniqueIdField(sidewalkLayer)
    index = createSidewalkSpatialIndex(sidewalkLayer)
    sidewalkIntersections = findSidewalkIntersections(sidewalkLayer, index)
    #deleteNonSidewalkGroups(sidewalkLayer)


def getUniqueIdList(layer):
    u_id = "u_id"
    ids = []
    uniqueIdFeatureDict = {}
    for feature in layer.getFeatures():
        uid = str(feature[u_id])
        ids.append(feature[u_id])
        if uid in uniqueIdFeatureDict:
            uniqueIdFeatureDict[uid].append(feature)
        else: 
            uniqueIdFeatureDict[uid] = [feature]
    uniqueIds = list(set(ids))
    return uniqueIds, uniqueIdFeatureDict


def createUniqueIdField(layer):
    if layer.dataProvider().fieldNameIndex("u_id") == -1:
        layer.dataProvider().addAttributes(
            [QgsField("u_id", QVariant.Int)]
        )
        layer.updateFields()


def createSidewalkSpatialIndex(sidewalkLayer):
    print("Generating spatial index...")
    index = QgsSpatialIndex()
    sidewalkLayerFeatures = sidewalkLayer.getFeatures()
    for feature in sidewalkLayerFeatures:
        index.insertFeature(feature)
    print("Index generated\n")
    return index


def findSidewalkIntersections(sidewalkLayer, index):
    #allAttributes = sidewalkLayer.pendingAllAttributesList()
    #sidewalkLayer.select(allAttributes)
    print("Getting feature list...")
    sidewalks = {feature.id(): feature for (feature) in sidewalkLayer.getFeatures()}
    print("Got feature list\n")
    dataProvider = sidewalkLayer.dataProvider()
    idIndex = dataProvider.fields().indexFromName("u_id")
    x = 0
    xx = 0
    uniqueId = 0

    print("Assigning ids...")

    updateMap = {}
    #lines will be removed from the list of sidewalks as they are
    #used, thus eventually the list variable sidewalks will reach length 0
    #indicating that all lines have been accounted for:
    start = time.time()
    last = 0
    secondsList = []
    while len(sidewalks.values()) > 0:
        line = sidewalks.values()[0]
        x += 1
        xx += 1
        if x % 1000 == 0:
            seconds = time.time() - start
            newLines = xx-last
            print("TIME:")
            print(seconds)
            print("")
            print("New lines scanned: " + str(newLines))
            print("\nLine groups scanned: " + str(x))
            print("Total lines scanned: " + str(xx))
            last = xx
            print("Lines remaining: " + str(len(sidewalks.values())) + "\n")
            start = time.time()
            secondsList.append(newLines/seconds)
        if x % 10000 == 0:
            print("AVERAGES")
            print("Lines per second: " + str(sum(secondsList)/float(len(secondsList))))
        #Only lines with a NULL "u_id" field are considered, because
        #lines with values in this field have already been taken care of
        if not line["u_id"]:
            thisLineId = line.id()
            #get all lines that intersect this line
            thisLineIntersects = (
                index.intersects(line.geometry().boundingBox())
            )
            #if line has no intersects with other lines,
            #assign the line a unique ID alone:
            if len(thisLineIntersects) == 0:
                updateMap[thisLineId] = {idIndex: uniqueId}
                #dataProvider.changeAttributeValues(updateMap)
                sidewalks.pop(thisLineId, None)
            #otherwise, find all of the lines that intersect this line
            #and all of THOSE lines' intersecting lines... etc...
            else:
                #intersectingLineList holds lines that have been
                #taken care of, while toAdd holds lines that need
                #to be taken care of. In the first step of the loop,
                #both hold just the initial Line
                intersectingLineList = [thisLineId]
                toAdd = [thisLineId]
                while len(toAdd) > 0:
                    toAdd_temp = []
                    for lid in toAdd:
                        liIntersIds = index.intersects(
                            sidewalks[lid].geometry().boundingBox()
                        )
                        for intersectLineId in liIntersIds:
                            if intersectLineId in sidewalks:
                                if (
                                    sidewalks[intersectLineId].geometry()
                                    .intersects(sidewalks[lid].geometry())
                                ):
                                    if intersectLineId not in intersectingLineList:
                                        intersectingLineList.append(intersectLineId)
                                        toAdd_temp.append(intersectLineId)
                    toAdd = toAdd_temp
                #updateMap = {}
                for interLine in intersectingLineList:
                    updateMap[interLine] = {idIndex: uniqueId}
                    sidewalks.pop(interLine, None)
                    xx += 1
                xx -= 1
            uniqueId += 1
    dataProvider.changeAttributeValues(updateMap)


typeField = "CAS"
sidewalkType = "COM_17"

def deleteNonSidewalkGroups(sidewalkLayer):
    print("Deleting unneeded lines")
    print("Getting unique ids")
    [uniqueIds, uniqueIdFeatureDict] = getUniqueIdList(sidewalkLayer)
    print("got unique ids")
    deleteIds = []
    featuresScanned = 0
    for i in uniqueIds:
        if (len(uniqueIds) - uniqueIds.index(i)) % 10000 == 0:
            print("Id groups left to scan: " + str(len(uniqueIds) - uniqueIds.index(i)))
            print("Features scanned: " + str(featuresScanned))
            print("Features to delete: " + str(len(deleteIds)) + "\n")
        uid = str(i)
        lineGroup = uniqueIdFeatureDict[uid]
        isSidewalk = False
        groupIds = []
        for line in lineGroup:
            featuresScanned += 1
            groupIds.append(line.id())
            if sidewalkType in line[typeField]:
                isSidewalk = True
                break
        if not isSidewalk:
            deleteIds = deleteIds + groupIds
    print("Features to delete: " + str(len(deleteIds)))
    print("Deleting features...")
    sidewalkLayer.dataProvider().deleteFeatures(deleteIds)


def combineTouchingGroups():
    sidewalksLayer = getSidewalkLayer()
    print("creating index")
    index = createSidewalkSpatialIndex(sidewalksLayer)
    print("index created")
    [uniqueIds, uniqueIdFeatureDict] = getUniqueIdList(sidewalksLayer)
    dataProvider = sidewalksLayer.dataProvider()
    idIndex = dataProvider.fields().indexFromName("u_id")
    otherIntersects = False
    otherIntersectIds = []
    usedIds = []
    updateMap = {}
    print("starting loop")
    x = 0
    for key in uniqueIdFeatureDict:
        if x % 100 == 0:
            print(x)
        if key not in usedIds:
            thisId = key
            otherIntersects = False
            otherIntersectIds = []
            for line in uniqueIdFeatureDict[key]:
                thisLineIntersects = (
                    index.intersects(line.geometry().boundingBox())
                )
                for intersect in thisLineIntersects:
                    if intersect.geometry().intersects(line.geometry()):
                        otherId = str(intersect["u_id"])
                        otherIntersects = True
                        otherIntersectIds.append(otherId)
            if otherIntersects:
                for i in otherIntersectIds:
                    for oLine in uniqueIdFeatureDict[i]:
                        oLineId = oLine.id()
                        updateMap[oLineId] = {idIndex: thisId}
            usedIds += otherIntersectIds
            x += 1
    dataProvider.changeAttributeValues(updateMap)


def removeSingleFeatures():
    sidewalksLayer = getSidewalkLayer()
    print("Initial feature count: " + str(sidewalksLayer.featureCount()))
    singleFeatures = getSingleFeatures(sidewalksLayer)
    featuresToDelete = singleFeatures.values()
    print("\nFeatures to delete")
    print(featuresToDelete)
    sidewalksLayer.dataProvider().deleteFeatures([f.id() for f in featuresToDelete])
    print("Final feature count: " + str(sidewalksLayer.featureCount()))


def getSingleFeatures(layer):
    seenIds = {}
    repeatIds = [] 
    singleFeatures = {}
    for feature in layer.getFeatures():
        feature_uid = feature["u_id"]
        if feature_uid not in repeatIds:
            if feature_uid not in seenIds:
                seenIds[feature_uid] = feature
            else:
                repeatIds.append(feature_uid)
    for i in seenIds:
    	if i not in repeatIds:
    		singleFeatures[i] = seenIds[i]
    return singleFeatures