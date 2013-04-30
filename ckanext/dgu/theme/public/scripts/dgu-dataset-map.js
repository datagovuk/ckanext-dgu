var CKAN = CKAN || {};

CKAN.DguDatasetMap = function($){

    // Private

    var getGeomType = function(feature){
        return feature.geometry.CLASS_NAME.split(".").pop().toLowerCase()
    }

    var getStyle = function(geom_type){
        var styles = CKAN.DguDatasetMap.styles;
        var style = (styles[geom_type]) ? styles[geom_type] : styles["default"];

        return new OpenLayers.StyleMap(OpenLayers.Util.applyDefaults(
                    style, OpenLayers.Feature.Vector.style["default"]))
    }

    // Public
    return {
        map: null,

        extent: null,

        styles: {
          /*
            "point":{
                "externalGraphic": "/ckanext/spatial/marker.png",
                "graphicWidth":14,
                "graphicHeight":25,
                "fillOpacity":1
            },
            */
            "default":{
                "fillColor":"#FCF6CF",
                "strokeColor":"#B52",
                "strokeWidth":2,
                "fillOpacity":0.4
            }
        },

        setup: function(){
            if (!this.extent)
                return false;

            var width = $("#dataset-map-container").width();
            var height = $("#dataset-map-container").height();
            /* It will not render in IE7 until it has a height.
             * OK, it has a height. top=0, bottom=0, therefore height=280
             * because that's the height of my parent container.
             * But no CSS height is set.
             * I hate you Microsoft. */
            $("#dataset-map-container").height(height);

            // Maximum extent available with the OS tiles, if the dataset falls outside,
            // the OSM global map will be loaded
            var os_max_bounds = new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00);

            var geojson_format = new OpenLayers.Format.GeoJSON();
            var features = geojson_format.read(this.extent);
            if (!features) return false;

            var dataset_bounds = features[0].geometry.getBounds();
            this.map_type = (os_max_bounds.containsBounds(dataset_bounds)) ? 'os' : 'osm';

            var attributionBox = $('#dataset-map-attribution');
            assert(attributionBox.length>0);
            var controls = [
              new OpenLayers.Control.Attribution({div: attributionBox[0]})
            ];

            if (this.map_type=='osm') {
                var mapquestTiles = [
                    "http://otile1.mqcdn.com/tiles/1.0.0/osm/${z}/${x}/${y}.jpg",
                    "http://otile2.mqcdn.com/tiles/1.0.0/osm/${z}/${x}/${y}.jpg",
                    "http://otile3.mqcdn.com/tiles/1.0.0/osm/${z}/${x}/${y}.jpg",
                    "http://otile4.mqcdn.com/tiles/1.0.0/osm/${z}/${x}/${y}.jpg"];

                var layers = [
                  new OpenLayers.Layer.OSM("MapQuest-OSM Tiles", mapquestTiles, {
                    attribution: 'Map data CC-BY-SA by <a href="http://openstreetmap.org">OpenStreetMap</a> | ' +
                    'Tiles by <a href="http://www.mapquest.com">MapQuest</a>'
                  })
                ];

                // Create a new map
                this.map = new OpenLayers.Map("dataset-map-container" ,
                    {
                    "projection": new OpenLayers.Projection("EPSG:900913"),
                    "displayProjection": new OpenLayers.Projection("EPSG:4326"),
                    "units": "m",
                    "numZoomLevels": 18,
                    "maxResolution": 156543.0339,
                    "maxExtent": new OpenLayers.Bounds(-20037508, -20037508, 20037508, 20037508.34),
                    "controls": controls
                });
                var internalProjection = new OpenLayers.Projection("EPSG:900913");
            } else if (this.map_type=='os') {

                var copyrightStatements = "Contains Ordnance Survey data (c) Crown copyright and database right  [2012]." + "Contains Royal Mail data (c) Royal Mail copyright and database right [2012]." + "Contains bathymetry data by GEBCO (c) Copyright [2012]." + "Contains data by Land & Property Services (Northern Ireland) (c) Crown copyright [2012].";

                // Create a new map
                var layers = [
                  new OpenLayers.Layer.WMS("Geoserver layers - Tiled",
			this.tiles_url, {
                        LAYERS: 'InspireETRS89',
		        STYLES: '',
		        format: 'image/png',
		        tiled: true
                        }, {
		        buffer: 0,
		        displayOutsideMaxExtent: true,
		        isBaseLayer: true,
		        attribution: copyrightStatements,
                        transitionEffect: 'resize'
                        }
                  )
                ];
                OpenLayers.DOTS_PER_INCH = 90.71428571428572;

    		var options = {
			        size: new OpenLayers.Size(width, height),
                                scales: [15000000, 10000000, 5000000, 1000000, 250000, 75000],
			        maxExtent: os_max_bounds ,
			        restrictedExtent: os_max_bounds ,
			        tileSize: new OpenLayers.Size(250, 250),
			        units: 'degrees',
			        projection: "EPSG:4258",
              controls: controls
    		};

                this.map = new OpenLayers.Map("dataset-map-container", options);

                var internalProjection = new OpenLayers.Projection("EPSG:4258");
            }
            this.map.addLayers(layers);

            var geojson_format = new OpenLayers.Format.GeoJSON({
                "internalProjection": internalProjection,
                "externalProjection": new OpenLayers.Projection("EPSG:4326")
            });

            // Add the Dataset Extent box
            var features = geojson_format.read(this.extent)
            var geom_type = getGeomType(features[0])

            var vector_layer = new OpenLayers.Layer.Vector("Dataset Extent",
                {
                    "projection": new OpenLayers.Projection("EPSG:4326"),
                    "styleMap": getStyle(geom_type)
                }
            );

            this.map.addLayer(vector_layer);
            vector_layer.addFeatures(features);
            if (geom_type == "point"){
                this.map.setCenter(new OpenLayers.LonLat(features[0].geometry.x,features[0].geometry.y),
                                   this.map.numZoomLevels/2)
            } else {
                this.map.zoomToExtent(vector_layer.getDataExtent());
            }


        }
    }
}(jQuery)


//OpenLayers.ImgPath = "/ckanext/spatial/js/openlayers/img/";

