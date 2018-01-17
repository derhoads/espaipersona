import os
import sys
import PyQt4.QtCore
import PyQt4.QtGui
import qgis.core
import qgis.gui
from qgis.core import *
from qgis.gui import *
from osgeo import ogr, osr
from PyQt4.QtCore import *
from matlab import engine

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

def loadPointsLayer(path):
    points = QgsVectorLayer(path, 'points', 'ogr')
    QgsMapLayerRegistry.instance().addMapLayer(points)
    return points

def createEmptyPolyLayer():
    polygons = QgsVectorLayer("Polygon", "polygon", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(polygons)
    return polygons

input_path = "/Users/danielrhoads/Documents/work/in3/exec/input/sidewalks.shp"
output_path = "/Users/danielrhoads/Documents/work/in3/exec/result/sidewalks.shp"

print("Starting QIS...")
QgsApplication.initQgis()
point_layer = loadPointsLayer(input_path)
poly_layer = createEmptyPolyLayer()
print("QGIS started.\n")
[uniqueIds, uniqueIdFeatureDict] = getUniqueIdList(point_layer)
print("Starting MATLAB...")
eng = matlab.engine.start_matlab()
print("MATLAB started.\n")

for uid in uniqueIdFeatureDict:
    point_xs = []
    point_ys = []
    for point in uniqueIdFeatureDict[uid]:
        point_coords = point.geometry().asPoint()
        point_xs.append(point_coords[0])
        point_ys.append(point_coords[1])
    points_list = [point_xs, point_ys]
    hull = eng.getPointEnvelope(points_list)

eng.quit()
QgsApplication.exitQgis()
