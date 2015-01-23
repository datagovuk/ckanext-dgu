this.ckan.spatial_libs = this.ckan.spatial_libs || {}

/* ----------------------------------------------- */
/* ckanext-spatial search-query module duplication */
/* TODO remove once ckanext-spatial/dgu is updated */
/* ----------------------------------------------- */
this.ckan.module('spatial-query', function ($, _) {

    return {
        options: {
            i18n: {
            },
            default_extent: [[90, 180], [-90, -180]]
        },

        template: {
            buttons: [
                '<div id="dataset-map-edit-buttons">',
                '<a href="javascript:;" class="btn cancel">Cancel</a> ',
                '<a href="javascript:;" class="btn apply disabled">Apply</a>',
                '</div>'
            ].join('')
        },

        initialize: function () {
            var module = this;
            $.proxyAll(this, /_on/);

            var libname = this.options.map_config.spatial_lib || 'leaflet'
            this.spatial_lib = ckan.spatial_libs[libname]
            if (! this.spatial_lib) throw "Spatial lib implementation not found: "+libname

            var user_default_extent = this.el.data('default_extent');
            if (user_default_extent ){
                if (user_default_extent instanceof Array) {
                    // Assume it's a pair of coords like [[90, 180], [-90, -180]]
                    this.options.default_extent = user_default_extent;
                } else if (user_default_extent instanceof Object) {
                    // Assume it's a GeoJSON bbox
                    this.options.default_extent = this.spatial_lib.geojson2extent(user_default_extent)
                }
            }
            this.el.ready(this._onReady);
        },

        _getParameterByName: function (name) {
            var match = RegExp('[?&]' + name + '=([^&]*)')
                .exec(window.location.search);
            return match ?
                decodeURIComponent(match[1].replace(/\+/g, ' '))
                : null;
        },

        _drawExtentFromCoords: function(xmin, ymin, xmax, ymax) {
            if ($.isArray(xmin)) {
                var coords = xmin;
                xmin = coords[0]; ymin = coords[1]; xmax = coords[2]; ymax = coords[3];
            }
            return this.spatial_lib.drawExtentFromCoords(xmin, ymin, xmax, ymax);
        },

        _drawExtentFromGeoJSON: function(geom) {
            return this.spatial_lib.drawExtentFromGeoJSON(geom);
        },

        _onReady: function() {
            var module = this;
            var map;
            var previous_extent;
            var is_exanded = false;
            var form = $("#dataset-search");
            // CKAN 2.1
            if (!form.length) {
                form = $(".search-form");
            }
            // looking for mini side search
            if (!form.length) {
                form = $(".form-search");
            }

            var buttons;

            // Add necessary fields to the search form if not already created
            $(['ext_bbox', 'ext_prev_extent']).each(function(index, item){
                if ($("#" + item).length === 0) {
                    $('<input type="hidden" />').attr({'id': item, 'name': item}).appendTo(form);
                }
            });

            // OK map time
            var spatial_lib = this.spatial_lib
            map = spatial_lib.createMap('dataset-map-container', this.options.map_config, true)

            // OK add the expander
            map.onDrawEnable(function(e) {
                if (!is_exanded) {
                    $('body').addClass('dataset-map-expanded');
                    map.reset();
                    is_exanded = true;
                }
            })

            // Setup the expanded buttons
            buttons = $(module.template.buttons).insertAfter(module.el);

            // Handle the cancel expanded action
            $('.cancel', buttons).on('click', function() {
                $('body').removeClass('dataset-map-expanded');
                map.clearSelection()
                setPreviousExtent();
                setPreviousBBBox();
                map.reset();
                is_exanded = false;
            });

            // Handle the apply expanded action
            $('.apply', buttons).on('click', function() {
                if (map.getSelection()) {
                    $('body').removeClass('dataset-map-expanded');
                    is_exanded = false;
                    map.reset()
                    // Eugh, hacky hack.
                    setTimeout(function() {
                        map.fitToSelection();
                        submitForm();
                    }, 200);
                }
            });

            // When user finishes drawing the box, record it and add it to the map
            map.onSelect(function(geom) {
                $('#ext_bbox').val(spatial_lib.geom2bboxstring(geom));
                $('.apply', buttons).removeClass('disabled').addClass('btn-primary');
            })

            // Record the current map view so we can replicate it after submitting
            map.onMoveEnd( function(e) {
                $('#ext_prev_extent').val(spatial_lib.extent2bboxstring(map.getExtent()));
            });

            // Ok setup the default state for the map
            var previous_bbox;
            setPreviousBBBox();
            setPreviousExtent();


            // Is there an existing box from a previous search?
            function setPreviousBBBox() {
                previous_bbox = module._getParameterByName('ext_bbox');
                if (previous_bbox) {
                    $('#ext_bbox').val(previous_bbox);
                    var previousBBox = module._drawExtentFromCoords(previous_bbox.split(','))
                    map.setSelectedGeom(previousBBox)
                    map.fitToSelection()
                }
            }

            // Is there an existing extent from a previous search?
            function setPreviousExtent() {
                previous_extent = module._getParameterByName('ext_prev_extent');
                if (previous_extent) {
                    coords = previous_extent.split(',');
                    map.fitToExtent(parseFloat(coords[0]), parseFloat(coords[1]), parseFloat(coords[2]), parseFloat(coords[3]));
                } else {
                    if (!previous_bbox){
                        map.fitToExtent(
                            module.options.default_extent[0][1],
                            module.options.default_extent[0][0],
                            module.options.default_extent[1][1],
                            module.options.default_extent[1][0]);
                    }
                }
            }

            // Add the loading class and submit the form
            function submitForm() {
                setTimeout(function() {
                    form.submit();
                }, 800);
            }
        }
    }
});


this.ckan.spatial_libs.dgu_ol3 = function() {

    var COPYRIGHT_STATEMENTS =
        "Contains Ordnance Survey data &copy; Crown copyright and database right  [2012].<br/>" +
        "Contains Royal Mail data &copy; Royal Mail copyright and database right [2012].<br/>" +
        "Contains bathymetry data by GEBCO &copy; Copyright [2012].<br/>" +
        "Contains data by Land & Property Services (Northern Ireland) &copy; Crown copyright [2012]."

    var geojsonFormat = new ol.format.GeoJSON()

    // Bounding box of our TMS that define our area of interest
    // Extent of the map in units of the projection
    var extent = [-30, 48.00, 3.50, 64.00];

    // Fixed resolutions to display the map at (pixels per ground unit)
    var resolutions = [0.03779740088, 0.02519826725, 0.01259913362, 0.00251982672, 0.00062995668, 0.000188987];

    // Define British National Grid Proj4js projection (copied from http://epsg.io/27700.js)
    //proj4.defs("EPSG:27700","+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +towgs84=446.448,-125.157,542.06,0.15,0.247,0.842,-20.489 +units=m +no_defs");
    proj4.defs("EPSG:4258", "+title=ETRS89 +proj=longlat +ellps=GRS80 +no_defs");

    var EPSG_4326 = ol.proj.get('EPSG:4326');
    var EPSG_4258 = ol.proj.get('EPSG:4258');

    var GAZETEER_PROJ = EPSG_4326

    EPSG_4258.setExtent(extent);

    return {

        bbox2geom: function(xmin, ymin, xmax, ymax, projection) {
            var e = ol.extent.boundingExtent([[xmin,ymin],[xmax,ymax]])
            // make sure the gazetteer extents are transformed into the system SRS
            if (projection) e = ol.proj.transformExtent(e, projection, EPSG_4258)
            var size = ol.extent.getSize(e)
            // either a point or a box
            return geom = size[0]*size[1] == 0 ?
                new ol.geom.Point(ol.extent.getCenter(e)) :
                new ol.geom.Polygon([[ol.extent.getBottomLeft(e), ol.extent.getTopLeft(e), ol.extent.getTopRight(e), ol.extent.getBottomRight(e)]])
        },

        /* spatial_lib implementation */
        geojson2extent: function(geojson) {
            //TODO
            throw "not implemented"
        },
        geom2bboxstring: function(geom) {
            return this.extent2bboxstring(geom.getExtent())
        },
        extent2bboxstring: function(extent) {
            return extent.join(',')
        },
        drawExtentFromCoords: function(xmin, ymin, xmax, ymax) {
            return this.bbox2geom(xmin, ymin, xmax, ymax)
        },
        drawExtentFromGeoJSON: function(geom) {
            //TODO
            throw "not implemented"
        },
        createMap: function(container, config, enableDraw) {


            // Define a TileGrid to ensure that WMS requests are made for
            // tiles at the correct resolutions and tile boundaries
            var tileGrid = new ol.tilegrid.TileGrid({
                origin: extent.slice(0, 2),
                resolutions: resolutions,
                tileSize: 250
            });

            var selectionFill = new ol.style.Fill({color: 'rgba(0, 0, 255, 0.2)'})
            var selectionStroke = new ol.style.Stroke({
                color: 'rgba(0, 0, 255, 0.6)',
                width: 1
            })

            var activatedFill = new ol.style.Fill({color: 'rgba(200, 200, 0, 0.2)'})
            var activatedStroke = new ol.style.Stroke({
                color: 'rgba(255, 50, 0, 0.6)',
                width: 1
            })

            // Create layer to hold the selected bbox
            var selectBoxSource = new ol.source.Vector();
            var selectionLayer = new ol.layer.Vector({
                source: selectBoxSource,
                style: new ol.style.Style({
                    fill: selectionFill,
                    stroke: selectionStroke,
                    image: new ol.style.Circle({
                        fill: selectionFill,
                        stroke: selectionStroke,
                        radius: 5
                    })
                })
            })

            // Create layer to hold the highlighted bbox
            var activateBoxSource = new ol.source.Vector();
            var activateLayer = new ol.layer.Vector({
                source: activateBoxSource,
                style: new ol.style.Style({
                    fill: activatedFill,
                    stroke: activatedStroke,
                    image: new ol.style.Circle({
                        fill: activatedFill,
                        stroke: activatedStroke,
                        radius: 5
                    })
                })
            })

            var OS_Attribution = new ol.Attribution({html: COPYRIGHT_STATEMENTS})

            var map = new ol.Map({
                target: container,
                size: [400,300],
                controls: ol.control.defaults( {attributionOptions: ({collapsible: false}) }),
                layers: [
                    new ol.layer.Tile({
                        source: new ol.source.TileWMS({
                            attributions: [
                                OS_Attribution
                            ],
                            //TODO : should the OS key stay here?
                            url: 'http://osinspiremappingprod.ordnancesurvey.co.uk/geoserver/gwc/service/wms?key=0822e7b98adf11e1a66e183da21c99ac',
                            params: {
                                'LAYERS': 'InspireETRS89',
                                'FORMAT': 'image/png',
                                'TILED': true,
                                'VERSION': '1.1.1'
                            },
                            tileGrid: tileGrid
                        })
                    }),
                    //vector,
                    selectionLayer,
                    activateLayer
                ],
                view: new ol.View({
                    projection: EPSG_4258,
                    resolutions: resolutions,
                    center: [-0.6680291327536106, 51.33129296535873],
                    zoom: 3
                })
            });

            var selectionListener = null
            var onDrawEnableListener = null

            var mapComponent = {
                onSelect: function(listener) {
                    selectionListener = listener
                },

                onDrawEnable: function(callback) {
                    onDrawEnableListener = callback
                },
                onMoveEnd: function(callback) {
                    map.on('moveend', callback);
                },

                setSelectedGeom: function(geom, updateExtent) {
                    selectBoxSource.clear()
                    selectBoxSource.addFeature(new ol.Feature(geom ))

                    var selectedExtent = selectBoxSource.getExtent()

                    if (updateExtent) {
                        var size = ol.extent.getSize(selectedExtent)
                        var bufferedExtent = ol.extent.buffer(
                            selectedExtent,
                                size[0]*size[1] == 0 ?
                                0.1 :                     // for a Point : arbitrary 0.1deg buffer
                                (size[0]+size[1])/20      // Polygon : 10% of mean size
                        )
                        map.getView().fitExtent(bufferedExtent, map.getSize())
                    }

                    if (this.coordinateInputs) {
                        for (var idx in this.coordinateInputs) this.coordinateInputs[idx].val(selectedExtent[idx].toFixed(5))
                    }
                },
                zoomIn: function() {
                    //TODO
                },
                reset: function() {
                    map.updateSize()
                },
                clearSelection: function() {
                    if (selectBoxSource) selectBoxSource.clear()
                },
                fitToExtent: function(minx, miny, maxx, maxy) {
                    map.getView().fitExtent([minx, miny, maxx, maxy], map.getSize())
                },
                fitToSelection: function() {
                    var extent = selectBoxSource.getExtent()
                    this.fitToExtent(extent[0], extent[1], extent[2], extent[3])
                },
                getSelection: function() {
                    return selectBoxSource.getFeatures()[0].getGeometry()
                },
                getExtent: function() {
                    return map.getView().calculateExtent(map.getSize())
                }
            }

            // Interaction to draw a bbox
            var boundingBoxInteraction = new ol.interaction.DragBox({
                condition: ol.events.condition.always,
                style: new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: [0, 0, 255, 1]
                    })
                })
            })

            boundingBoxInteraction.on('boxend', function (e) {
                var newBox = boundingBoxInteraction.getGeometry()

                mapComponent.setSelectedGeom(newBox, false)
                selectionListener && selectionListener(newBox)

                map.removeInteraction(boundingBoxInteraction);
                $(map.getViewport()).toggleClass('drawing', false)
            })

            var selectButton = $("<div class='selectButton ol-unselectable ol-control ol-collapsed' style='top: 4em; left: .5em;'><button class='ol-has-tooltip' type='button'><span class='glyphicon icon-crop' aria-hidden='true'></span><span role='tooltip'>Draw Selection</span></button></div>")
            $(".ol-viewport").append(selectButton)
            selectButton.click(function (e) {
                selectBoxSource.clear()
                map.addInteraction(boundingBoxInteraction)
                $(map.getViewport()).toggleClass('drawing', true)
                onDrawEnableListener && onDrawEnableListener()
            })

            return mapComponent
        }
    }
} ()