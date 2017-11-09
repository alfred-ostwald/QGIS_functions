from random import randrange
from qgis import *
from qgis.utils import *
from qgis.gui import *
import time

def print_test():
	print "hello world"

def colour_code(layer, attribute):
	#colour_code("accident", "severity")
	start_time = time.asctime()
	start_timer = time.time()
	print "start_time: ", start_time

	lyr = core.QgsMapLayerRegistry.instance().mapLayersByName(layer)[0]
	
	fni = lyr.fieldNameIndex(attribute)
	unique_values = lyr.dataProvider().uniqueValues(fni)
	
	categories = []
	
	for val in unique_values:
				
		symbol = core.QgsSymbolV2.defaultSymbol(lyr.geometryType())
		
		layer_style = {}
		# instead of this want to use user-defined styles
		if val == 1:	#fatal -> red
			layer_style['color'] = '255,0,0'
		elif val == 2:	#serious -> orange
			layer_style['color'] = '255,128,0'
		elif val == 3:	#slight -> green
			layer_style['color'] = '0,255,0'
		else:
			layer_style['color'] = '%d, %d, %d' % (randrange(0,256), randrange(0,256),\
			randrange(0,256))
		
		layer_style['outline'] = '#000000'
		symbol_layer = core.QgsSimpleFillSymbolLayerV2.create(layer_style)

		if symbol_layer is not None:
			symbol.changeSymbolLayer(0, symbol_layer)

		category = core.QgsRendererCategoryV2(val, symbol, str(val))
		categories.append(category)

	renderer = core.QgsCategorizedSymbolRendererV2(attribute, categories)

	if renderer is not None:
		lyr.setRendererV2(renderer)

	if lyr.rendererV2().type() == 'categorizedSymbol':
		lyr.triggerRepaint()
		end_time = time.asctime()
		end_timer = time.time()
		time_diff = end_timer - start_timer
		print "end time: ", end_time
		print "time taken: ", time_diff
				
	

def get_subsel(layer,switch_off,filter):

# get_subsel("accident", True, "\"accdate\" >= '1990-01-01' AND \"accdate\" <= '1992-12-31'")
# get_subsel("accident", True, "\"date\" >= '1990-01-01' AND \"date\" <= '1992-12-31'")
	start_time = time.asctime()
	start_timer = time.time()
	print "start_time: ", start_time
	
	legend = iface.legendInterface()
	lyr = core.QgsMapLayerRegistry.instance().mapLayersByName(layer)[0] #[0] at back to select 1st item in list
	crs = lyr.crs().authid()
	
	new_layer = core.QgsVectorLayer("Point?crs={0}".format(crs),"acc_subselection", "memory")
	
	if switch_off:
		legend.setLayerVisible(lyr,False)
	
	request = core.QgsFeatureRequest().setFilterExpression(filter)
	
	iter = lyr.getFeatures(request)
	selected_feats = [f for f in iter]

	data_prov = new_layer.dataProvider()
	data_prov.addFeatures(selected_feats)

	core.QgsMapLayerRegistry.instance().addMapLayer(new_layer)

	end_time = time.asctime()
	end_timer = time.time()
	time_diff = end_timer - start_timer
	print "end time: ", end_time
	print "time taken: ", time_diff
	

def get_clusters(layer, out_layer, buff_size, acc_threshold):

	source_layer = core.QgsMapLayerRegistry.instance().mapLayersByName(layer)[0]
	# get the crs
	CRS = source_layer.crs().authid()
	# make new layer for storing clusters
	cluster_layer = QgsVectorLayer("Polygon?crs={0}".format(CRS), out_layer, "memory")
	cluster_layer.setLayerTransparency(50)
	cdp = cluster_layer.dataProvider()
	
	# set up loop for accidents in source_layer
	for acc_feat in source_layer.getFeatures():
		buffer = acc_feat.geometry().buffer(50,50) #distance,segments
		f = QgsFeature()
		f.setGeometry(buffer)
		cdp.addFeatures([f])
		# this just for one, would want to add all feats to list before adding them to new
		# layer
	
	
def write_point_coords(layer, out_file):

	lay = core.QgsMapLayerRegistry.instance().mapLayersByName(layer)[0]
	
	if lay.wkbType() == QGis.WKBPoint:
		output_file = open(out_file, 'w')
		for feature in lay.getFeatures():
			geom = feature.geometry()
			line = '%f, %f\n' % (geom.asPoint().x(), geom.asPoint().y())
			unicode_line = line.encode('utf-8')
			output_file.write(unicode_line)
		
		output_file.close()
	else:
		print "Wrong geometry type!"
		return False

def KD_clusters(layer, out_file, buff_size, acc_threshold, out_layer):
	
	#KD_clusters("accident", "C:\QGIS_testing\clusters.csv",50,3,"clusters")
	
	import os.path
	from scipy import loadtxt
	from scipy.spatial import KDTree
	
	start_time = time.asctime()
	start_timer = time.time()
	print "start_time: ", start_time	
	
	lay = core.QgsMapLayerRegistry.instance().mapLayersByName(layer)[0]
	no_of_skips = 0
	
	#if lay.wkbType() == QGis.WKBPoint:
	output_file = open(out_file, 'w')
	for feature in lay.getFeatures():
		if feature.isValid() == True:
			#print feature.id()
			geom = feature.geometry()
			try:
				line = '%f, %f\n' % (geom.asPoint().x(), geom.asPoint().y())
				unicode_line = line.encode('utf-8')
				output_file.write(unicode_line)
			except AttributeError:
				print "skip this one", feature.id()
				no_of_skips += 1
		else:
			print "skipping feature", feature.id()
	
	output_file.close()
	#else:
	#	raise IOError, "Wrong geometry type!"
		
	if not os.path.exists(out_file):
		raise IOError, "Coords file not found, unable to continue"
		
	data = loadtxt(out_file, delimiter = ',')
	tree = KDTree(data)
	clusters = []
	
	for point in data:
		if len(tree.query_ball_point(point, buff_size)) >= acc_threshold:
			clusters.append(point)
			
	if len(clusters) > 0:
		print "getting layer CRS info"
		# get the crs
		CRS = lay.crs().authid()
		print "got it"
		# make new layer for storing clusters
		print "defining new layer..."
		cluster_layer = core.QgsVectorLayer("Polygon?crs={0}".format(CRS), out_layer, "memory")
		print "defined it"
		cluster_layer.setLayerTransparency(50)
		cdp = cluster_layer.dataProvider()
		cluster_layer.startEditing()
		
		for cluster in clusters:
			feat = core.QgsFeature()
			feat.setGeometry(QgsGeometry.fromPoint(core.QgsPoint(cluster[0],cluster[1])).\
			buffer((buff_size/2),50))
				
			cdp.addFeatures([feat])
		
		cluster_layer.commitChanges()
		
		#os.remove(out_file)
	core.QgsMapLayerRegistry.instance().addMapLayer(cluster_layer)
	#core.QgsMapCanvas.refresh()
	end_time = time.asctime()
	end_timer = time.time()
	time_diff = end_timer - start_timer
	print "end time: ", end_time
	print "time taken: ", time_diff
	print "accidents skipped: ", no_of_skips

def find_acc(layer, expression, scale = 2500):
	
	#find_acc("accident", "\"Police_ref\" = '110246669'", 2500)
	
	start_time = time.asctime()
	start_timer = time.time()
	print "start_time: ", start_time
	
	lay = core.QgsMapLayerRegistry.instance().mapLayersByName(layer)[0]
	canvas = iface.mapCanvas()
	
	request = core.QgsFeatureRequest().setFilterExpression(expression)
	iter = lay.getFeatures(request)
	
	selection = [f for f in iter]
	
	if len(selection) == 1:
		print "Found accident"
		accident = selection[0]
	else:
		raise IOError, "More than 1 accident found"
	
	lay.setSelectedFeatures([accident.id()])
	canvas.zoomToSelected()
	#canvas.refresh()
	canvas.zoomScale(scale)
	
	end_time = time.asctime()
	end_timer = time.time()
	time_diff = end_timer - start_timer
	print "end time: ", end_time
	print "time taken: ", time_diff

