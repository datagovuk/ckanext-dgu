
$(function() {
    var ckan = window.ckan
    ckan.spatial_libs = ckan.spatial_libs || {}

    /* ----------------------------------------------- */
    /* ckanext-spatial search-query module duplication */
    /* TODO remove once ckanext-spatial/dgu is updated */
    /* ----------------------------------------------- */

    ckan.DGU = ckan.DGU || {}
    var DguSearch = ckan.DGU.SearchModule = function() {
        this.options = {
            i18n: {},
            default_extent: [[49.90961, -13.69136], [60.84755, 1.77171]]
        }
    }

    var initCallbacks = []
    DguSearch.onReady = function(callback) {
        initCallbacks.push(callback)
    }
    DguSearch.prototype = {

        template: {
            buttons:
                '<div id="dataset-map-edit-buttons">' +
                '<a href="javascript:;" class="btn cancel">Cancel</a> ' +
                '<a href="javascript:;" class="btn apply disabled">Apply</a>' +
                '</div>'
        },

        initialize: function () {
            var module = this;
            $.proxyAll(this, /_on/);

            var libname = 'dgu_ol3' // this.options.map_config.spatial_lib || 'leaflet'
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

        // Add the loading class and submit the form
        submitForm: function() {
            var _this = this
            setTimeout(function() {
                _this.form.submit();
            }, 800);
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

            this.form = form

            var buttons;

            // Add necessary fields to the search form if not already created
            $(['ext_bbox', 'ext_prev_extent', 'ext_gazname']).each(function(index, item){
                if ($("#" + item).length === 0) {
                    $('<input type="hidden" />').attr({'id': item, 'name': item}).appendTo(form);
                }
            });

            // OK map time
            var spatial_lib = this.spatial_lib
            // put map in module instance for later reference to display results bboxes
            this.map = map = spatial_lib.createMap('dataset-map-container', this.options.map_config, true)

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
                map.disableDraw()
                map.clearSelection()
                map.disableDraw && map.disableDraw()
                setPreviousExtent();
                setPreviousBBBox();
                map.reset();
                is_exanded = false;
                buttons.hide()
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
                        module.submitForm();
                    }, 200);
                }
            });

            var currentSelectedGeom

            var positionBBoxButtons = function(bboxExtent) {
                if (!bboxExtent && currentSelectedGeom) bboxExtent = currentSelectedGeom.getExtent()

                if (bboxExtent && is_exanded) {
                    var topRightCorner = ol.extent.getTopRight(bboxExtent)
                    var screenPos = map.getPixelFromCoordinate(topRightCorner)

                    var top = screenPos[1]
                    var left = screenPos[0]
                    var mapContainer = buttons.offsetParent().find("#dataset-map-container")
                    if (top < 0 || top > mapContainer.height() - buttons.height()) top = 0
                    if (left < 0 || left > mapContainer.width() - buttons.width()) left = buttons.offsetParent().find(".dataset-map").width() - buttons.width()
                    buttons.css('left', left + mapContainer.position().left)
                    buttons.css('top', top + mapContainer.position().top)
                }
            }

            // When user finishes drawing the box, record it and add it to the map
            map.onSelect(function(geom) {
                currentSelectedGeom = geom
                $('#ext_bbox').val(spatial_lib.geom2bboxstring(geom))
                if (is_exanded) {
                    $('.apply', buttons).removeClass('disabled').addClass('btn-primary')
                    positionBBoxButtons()
                    buttons.show()
                }
            })

            map.getOL3Map().on('pointerdrag', function(e) {positionBBoxButtons()})
            map.getOL3Map().on('moveend', function(e) {positionBBoxButtons()})
            map.getOL3Map().getView().on('change:resolution', function(e) {positionBBoxButtons()})

            /*
            // Record the current map view so we can replicate it after submitting
            map.onMoveEnd( function(e) {
                $('#ext_prev_extent').val(spatial_lib.extent2bboxstring(map.getExtent()));
            });
            */

            // Ok setup the default state for the map
            var previous_bbox;
            setPreviousBBBox();
            setPreviousExtent();
            map.fitToResults();

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
                    map.fitToExtent([parseFloat(coords[0]), parseFloat(coords[1]), parseFloat(coords[2]), parseFloat(coords[3])]);
                } else {
                    if (!previous_bbox){
                        map.fitToExtent([
                            module.options.default_extent[0][1],
                            module.options.default_extent[0][0],
                            module.options.default_extent[1][1],
                            module.options.default_extent[1][0]]);
                    }
                }
            }

            var thisModule = this
            $.each(initCallbacks, function(idx, callback) {callback(thisModule)})
        }
    }


    ckan.module('spatial-query', function ($, _) {
        return new DguSearch()
    });


    ckan.spatial_libs.dgu_ol3 = function() {

        var geocoderServiceUrl = 'http://unlock.edina.ac.uk/ws/search?minx=-20.48&miny=48.79&maxx=3.11&maxy=62.66&format=json&name='
        var COPYRIGHT_STATEMENTS =
            "Map background contains data from:<br/>" +
            "Ordnance Survey &copy; Crown copyright and database right [2012];<br/>" +
            "Royal Mail &copy; Royal Mail copyright and database right [2012];<br/>" +
            "Bathymetry by GEBCO &copy; Copyright [2012];<br/>" +
            "Land & Property Services (Northern Ireland) &copy; Crown copyright [2012]."

        var geojsonFormat = new ol.format.GeoJSON()

        var OSLayers = {
            INSPIRE_Vector_4326 : {
                extent: [-180,-90,180,90],
                resolutions: [0.703125,0.3515625,0.17578125,0.087890625,0.0439453125,0.02197265625,0.010986328125,0.0054931640625,0.00274658203125,0.001373291015625,6.866455078125E-4,3.4332275390625E-4,1.71661376953125E-4,8.58306884765625E-5,4.291534423828125E-5,2.1457672119140625E-5,1.0728836059570312E-5,5.364418029785156E-6,2.682209014892578E-6,1.341104507446289E-6],
                tileSize: 256,
                clippingExtent: [-29.5, 48.5, 3.3, 64.00],
                wmsLayerName: 'InspireVectorStack',
                projection: 'EPSG:4326'
            },
            INSPIRE_Vector_Mercator : {
                extent: [-2.003750834E7,-2.003750834E7,2.0037508345578495E7,2.0037508345578495E7],
                resolutions: [156543.033928041,78271.51696402048,39135.75848201023,19567.87924100512,9783.93962050256,4891.96981025128,2445.98490512564,1222.99245256282,611.49622628141,305.7481131407048,152.8740565703525,76.43702828517624,38.21851414258813,19.10925707129406,9.554628535647032,4.777314267823516,2.388657133911758,1.194328566955879,0.5971642834779395],
                tileSize: 256,
                //clippingExtent: [-12, 50.00, 3, 60.00],
                wmsLayerName: 'InspireVectorStack',
                projection: 'EPSG:900913'
            },
            INSPIRE_WGS84 : {
                extent: [-30, 48.00, 7.79, 64.00],
                resolutions: [0.037797400884406626,0.025198267256271084,0.012599133628135542,0.0025198267256271085,6.299566814067771E-4,1.889870044220331E-4,1.259913362813554E-4,6.29956681406777E-5,2.5198267256271077E-5],
                tileSize: 250,
                clippingExtent: [-29.5, 48.5, 3.3, 64.00],
                wmsLayerName: 'InspireWGS84',
                projection: 'EPSG:4326'
            },
            INSPIRE_ETRS89 : {
                extent: [-30, 48.00, 7.79, 64.00],
                resolutions: [0.037797400884406626,0.025198267256271084,0.012599133628135542,0.0025198267256271085,6.299566814067771E-4,1.889870044220331E-4,1.259913362813554E-4,6.29956681406777E-5,2.5198267256271077E-5],
                tileSize: 250,
                clippingExtent: [-29.5, 48.5, 3.3, 64.00],
                wmsLayerName: 'InspireETRS89',
                projection: 'EPSG:4258'
            }
        }

        // Resolutions for the basemap to complement the OS layer
        var global_resolutions = [1.40625, 0.703125,0.3515625,0.17578125,0.0878906250,0.05]

        // Define British National Grid Proj4js projection (copied from http://epsg.io/27700.js)
        //proj4.defs("EPSG:27700","+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +towgs84=446.448,-125.157,542.06,0.15,0.247,0.842,-20.489 +units=m +no_defs");
        proj4.defs("EPSG:4258", "+title=ETRS89 +proj=longlat +ellps=GRS80 +no_defs");

        var activeLayer = OSLayers.INSPIRE_WGS84 // OSLayers.INSPIRE_Vector_4326

        var EPSG_4326 = ol.proj.get('EPSG:4326');
        var MAP_PROJ = ol.proj.get(activeLayer.projection);
        var GAZETEER_PROJ = EPSG_4326

        // take global resolutions above the OS layer supported resolutions to fill the gap
        var resolutions = []
        $.each(global_resolutions, function(idx, res) {
            if (res > activeLayer.resolutions[0]) resolutions.push(res)
        })
        resolutions = resolutions.concat(activeLayer.resolutions)


        var spatial_lib = {

            bbox2geom: function(xmin, ymin, xmax, ymax, projection) {
                var e = ol.extent.boundingExtent([[xmin,ymin],[xmax,ymax]])
                // make sure the gazetteer extents are transformed into the system SRS
                if (projection) e = ol.proj.transformExtent(e, projection, MAP_PROJ)
                var size = ol.extent.getSize(e)
                // either a point or a box
                return geom = size[0]*size[1] == 0 ?
                    new ol.geom.Point(ol.extent.getCenter(e)) :
                    new ol.geom.Polygon([[ol.extent.getBottomLeft(e), ol.extent.getTopLeft(e), ol.extent.getTopRight(e), ol.extent.getBottomRight(e)]])
            },

            geojson2geom: function(geojson) {
                return geojsonFormat.readGeometry(geojson)
            },

            createGazetteerInput: function(inputEl, selectCallback, hoverCallback) {
                var spinner = $(
                    "<div class='spinner' style='position: absolute;right: 1em;top: 9px; display: none'>" +
                        "<div class='rect1'></div>" +
                        "<div class='rect2'></div>" +
                        "<div class='rect3'></div></div>")
                spinner.insertAfter($(inputEl))

                var currentQuery
                $(inputEl)
                    .autocomplete({
                        triggerSelectOnValidInput : false,
                        minChars: 3,
                        appendTo: '#gazetteer',
                        showNoSuggestionNotice: true,
                        preserveInput: true,
                        serviceUrl: function(token) {
                            return geocoderServiceUrl + token + "*"},
                        paramName: 'query',
                        dataType: 'jsonp',
                        noSuggestionNotice: '<i>No Results</i>',
                        onSearchStart: function(params) {
                            currentQuery = params['query']
                            spinner.show()
                        },
                        onSearchComplete: function(q, suggestions) {
                            currentQuery = undefined
                            spinner.hide()
                            // set min-width instead of width (list must be expandable to the right to allow for feature code display)
                            $("div.autocomplete-suggestions").css({"min-width": $("#gazetteer input").outerWidth()});
                        },
                        onSearchError: function(q, jqXHR, textStatus, errorThrown) {
                            if (q == currentQuery) // hide spinner only if the error is about the current query
                                spinner.hide()
                        },
                        formatResult: function(suggestion, currentValue) {
                            return "<div><div>"+suggestion.value+"</div><div>"+suggestion.data.properties.featuretype+"</div></div>"
                        },
                        transformResult: function(response) {
                            return {
                                suggestions: $.map(response.features, function(feature) {
                                    feature.bbox_geom = spatial_lib.bbox2geom(feature.bbox[0], feature.bbox[1], feature.bbox[2], feature.bbox[3], GAZETEER_PROJ)
                                    return { value: feature.properties.name, data: feature };
                                })
                            };
                        },
                        onSelect: function (suggestion) {
                            selectCallback && selectCallback(suggestion)
                        },
                        onActivate: function(item) {
                            hoverCallback && hoverCallback(item.data.bbox_geom)
                        }
                    })
                    .blur(function(e) {
                        hoverCallback && hoverCallback()
                    })
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
                return extent.slice(0).map(function(coord) {return coord.toFixed(6)}).join(',')
            },
            drawExtentFromCoords: function(xmin, ymin, xmax, ymax) {
                return this.bbox2geom(xmin, ymin, xmax, ymax)
            },
            drawExtentFromGeoJSON: function(geom) {
                //TODO
                throw "not implemented"
            },
            createMap: function(container, config, enableDraw) {

                // Create layer to hold the selected bbox
                var selectBoxSource = new ol.source.Vector();
                var selectionLayer = new ol.layer.Vector({
                    source: selectBoxSource,
                    style: [
                        new ol.style.Style({
                            fill: new ol.style.Fill({color: 'rgba(0, 0, 255, 0.03)'}),
                            stroke: new ol.style.Stroke({color: 'rgba(0, 0, 255, 0.6)', width: 1.5})
                        }),
                        new ol.style.Style({
                            stroke: new ol.style.Stroke({color: 'white', width: 0.5})
                        })
                    ]
                })

                var suggestionFill = new ol.style.Fill({color: 'rgba(200, 200, 0, 0.2)'})
                var suggestionStroke = new ol.style.Stroke({
                    color: 'rgba(255, 50, 0, 0.6)',
                    width: 1
                })
                // Create layer to hold bbox suggestions
                var suggestedBoxSource = new ol.source.Vector();
                var suggestionLayer = new ol.layer.Vector({
                    source: suggestedBoxSource,
                    style: new ol.style.Style({
                        fill: suggestionFill,
                        stroke: suggestionStroke,
                        image: new ol.style.Circle({
                            fill: suggestionFill,
                            stroke: suggestionStroke,
                            radius: 5
                        })
                    })
                })

                // Create layer to hold the highlighted bbox
                var resultsFill = new ol.style.Fill({color: 'rgba(139,198,58, 0.05)'})
                var resultsStroke = new ol.style.Stroke({color: 'rgba(0,0,0, 0.8)',width: 1.5})
                var resultsBboxSource = new ol.source.Vector();
                var resultsLayer = new ol.layer.Vector({
                    source: resultsBboxSource,
                    style: new ol.style.Style({
                        fill: resultsFill,
                        stroke: resultsStroke,
                        image: new ol.style.Circle({
                            fill: resultsFill,
                            stroke: resultsStroke,
                            radius: 5
                        })
                    })
                })

                var attributionHtml = "<span class='attributionHover'><span class='short'>Copyrights</span><span class='long'>"+COPYRIGHT_STATEMENTS+"</span></span>"
                var OS_Attribution = new ol.Attribution({html: attributionHtml})

                var OS_Layer = new ol.layer.Tile({
                    source: new ol.source.TileWMS({
                        attributions: [
                            OS_Attribution
                        ],
                        //TODO : should the OS key stay here?
                        url: 'http://osinspiremappingprod.ordnancesurvey.co.uk/geoserver/gwc/service/wms?key=0822e7b98adf11e1a66e183da21c99ac',
                        params: {
                            'LAYERS': activeLayer.wmsLayerName,
                            'FORMAT': 'image/png',
                            'TILED': true,
                            'VERSION': '1.1.1'
                        },
                        tileGrid: new ol.tilegrid.TileGrid({
                            origin: activeLayer.extent.slice(0, 2),
                            resolutions: activeLayer.resolutions,
                            tileSize: activeLayer.tileSize
                        })
                    }),
                    extent: activeLayer.extent,
                    maxResolution: activeLayer.resolutions[0]
                })

                if (activeLayer.clippingExtent) {
                    // The clipping geometry.
                    var OSClippingGeom = new ol.geom.Polygon([
                        [
                            [activeLayer.clippingExtent[0], activeLayer.clippingExtent[1]],
                            [activeLayer.clippingExtent[0], activeLayer.clippingExtent[3]],
                            [activeLayer.clippingExtent[2], activeLayer.clippingExtent[3]],
                            [activeLayer.clippingExtent[2], activeLayer.clippingExtent[1]]
                        ]
                    ])
                    // A style for the geometry.
                    var fillStyle = new ol.style.Fill({color: [0, 0, 0, 0]});

                    OS_Layer.on('precompose', function (event) {
                        var ctx = event.context;
                        var vecCtx = event.vectorContext;

                        ctx.save();

                        // Using a style is a hack to workaround a limitation in
                        // OpenLayers 3, where a geometry will not be draw if no
                        // style has been provided.
                        vecCtx.setFillStrokeStyle(fillStyle, null);
                        vecCtx.drawPolygonGeometry(OSClippingGeom);

                        ctx.clip();
                    });

                    OS_Layer.on('postcompose', function (event) {
                        var ctx = event.context;
                        ctx.restore();
                    });
                }

                var map = new ol.Map({
                    target: container,
                    size: [400,300],
                    controls: ol.control.defaults( {attributionOptions: ({collapsible: false}) }),
                    layers: [

                        new ol.layer.Tile({
                            source: new ol.source.TileWMS({
                                url: 'http://vmap0.tiles.osgeo.org/wms/vmap0',
                                params: {
                                    'VERSION': '1.1.1',
                                    'LAYERS': 'basic',
                                    'FORMAT': 'image/jpeg'
                                }
                            })
                        }),

                        OS_Layer,
                        //vector,
                        selectionLayer,
                        resultsLayer,
                        suggestionLayer
                    ],
                    view: new ol.View({
                        projection: MAP_PROJ,
                        resolutions: resolutions,
                        center: ol.proj.transform([-4.5, 54], EPSG_4326, MAP_PROJ),
                    })
                });
                map.getView().fitExtent(activeLayer.extent, map.getSize())

                var resultsOverlay = new ol.FeatureOverlay({
                    map: map,
                    style: (function() {
                        var stroke = new ol.style.Stroke({color: 'black' /* '#8bc658' */, width: 2.5})
                        var stroke2 = new ol.style.Stroke({color: 'white', width: 1})
                        var fill = new ol.style.Fill({color: 'rgba(139,198,58,0.2)'})
                        var textStroke = new ol.style.Stroke({color: '#fff',width: 2});
                        var textFill = new ol.style.Fill({color: '#000'});
                        return function(feature, resolution) {
                            return [new ol.style.Style({
                                stroke: stroke,
                                fill: fill,
                                image: new ol.style.Circle({
                                    fill: fill,
                                    stroke: stroke,
                                    radius: 5
                                }),
                                /* this can be used instead of tooltips
                                text: new ol.style.Text({
                                    font: '12px Calibri,sans-serif',
                                    text: feature.get('name'),
                                    fill: textFill,
                                    stroke: textStroke
                                })
                                */
                            }), new ol.style.Style({
                                stroke: stroke2,
                                image: new ol.style.Circle({
                                    stroke: stroke2,
                                    radius: 5
                                })
                            })];
                        };
                    })()
                });

                // override view function to prevent from panning outside the extent
                /* no need for constraint since we clip the layer
                map.getView().constrainCenter = function(center) {
                    var resolution = this.getResolution()
                    if (center !== undefined && resolution !== undefined) {
                        var mapSize = (map.getSize());
                        var viewResolution = resolution;
                        var mapHalfWidth = (mapSize[0] * viewResolution) / 2.0;
                        var mapHalfHeight = (mapSize[1] * viewResolution) / 2.0;
                        var extent = activeLayer.clippingExtent
                        if (mapHalfWidth >= (extent[2] - extent[0])/2) {
                            center[0] = extent[0] + (extent[2] - extent[0]) / 2
                        } else if (center[0] - mapHalfWidth < extent[0]) {
                            center[0] = extent[0] + mapHalfWidth;
                        } else if (center[0] + mapHalfWidth > extent[2]) {
                            center[0] = extent[2] - mapHalfWidth;
                        }

                        if (mapHalfHeight >= (extent[3] - extent[1])/2) {
                            center[1] = extent[1] + (extent[3] - extent[1]) / 2
                        } else if (center[1] - mapHalfHeight < extent[1]) {
                            center[1] = extent[1] + mapHalfHeight;
                        } else if (center[1] + mapHalfHeight > extent[3]) {
                            center[1] = extent[3] - mapHalfHeight;
                        }
                        return center;
                    } else {
                        return center;
                    }
                }
    */

                var info = $("<div id='featureInfo' style='position: absolute'></div>").appendTo($(map.getViewport()).parent())
                info.tooltip({
                    animation: false,
                    trigger: 'manual'
                });
                var highlightedResult
                var highlightFeature = function(feature) {
                    if (feature) {
                        if (feature !== highlightedResult) {
                            if (highlightedResult) {
                                resultsOverlay.removeFeature(highlightedResult)
                                $(".dataset-summary.highlighted").toggleClass("highlighted", false)
                            }
                            resultsOverlay.addFeature(highlightedResult = feature)

                            $(".dataset-summary[data-id='"+feature.getId()+"']").toggleClass("highlighted", true)
                        }
                    } else {
                        if (highlightedResult) {
                            resultsOverlay.removeFeature(highlightedResult)
                            $(".dataset-summary.highlighted").toggleClass("highlighted", false)
                            highlightedResult = undefined
                        }
                    }
                }

                var highlightGeom = function(geom) {
                    suggestedBoxSource.clear()
                    if (geom) {
                        suggestedBoxSource.addFeature(new ol.Feature(geom ))
                    }
                }

                var isDrawing

                $(map.getViewport()).on('click', function(evt) {
                    if (!isDrawing && !$('body').hasClass('dataset-map-expanded')) {
                        var pixel = map.getEventPixel(evt.originalEvent)

                        var feature = map.forEachFeatureAtPixel(
                            pixel,
                            function (feature, layer) {
                                return feature
                            },
                            undefined,
                            function (layer) {
                                return layer.getSource() === resultsBboxSource
                            })
                        if (feature) {
                            $(".dataset-summary[data-id='" + feature.getId() + "']>a")[0].click()
                        }
                    }
                })

                $(map.getViewport()).on('mousemove', function(evt) {
                    var pixel = map.getEventPixel(evt.originalEvent)

                    var feature = map.forEachFeatureAtPixel(
                        pixel,
                        function(feature, layer) {return feature},
                        undefined,
                        function(layer) { return layer.getSource() === resultsBboxSource})

                    highlightFeature(feature)
                    if (feature) {
                        info.css({
                            left: pixel[0] + 'px',
                            top: (pixel[1] - 5) + 'px'
                        });
                        info.tooltip('hide')
                            .attr('data-original-title', feature.get('name'))
                            .tooltip('fixTitle')
                            .tooltip('show')
                        !isDrawing && $(map.getViewport()).css("cursor", "pointer");
                    } else {
                        info.tooltip('hide')
                        $(map.getViewport()).css("cursor", "");
                    }
                })

                $(map.getViewport()).on('mouseout', function(evt) {
                    highlightFeature()
                    info.tooltip('hide')
                })

                var selectionListener = null
                var onDrawEnableListener = null

                // Interaction to draw a bbox
                var boundingBoxInteraction = new ol.interaction.DragBox({
                    condition: ol.events.condition.always,
                    style: new ol.style.Style({
                        stroke: new ol.style.Stroke({
                            color: [0, 0, 255, 1]
                        })
                    })
                })

                var mapComponent = {

                    getOL3Map: function() {
                        return map
                    },

                    highlightResult: function(id) {
                        var feature = id && resultsBboxSource.getFeatureById(id)
                        highlightFeature(feature)
                    },

                    highlightGeom: function(geom) {
                        highlightGeom(geom)
                    },

                    fitToResults: function() {
                        if (resultsBboxSource && resultsBboxSource.getFeatures().length > 0) {
                            var extent = resultsBboxSource.getExtent()
                            this.fitToExtent(extent, 0.05, true)
                        }
                    },

                    enableDraw: function() {
                        selectBoxSource.clear()
                        if (map.getInteractions().getArray().indexOf(boundingBoxInteraction) == -1) {
                            map.addInteraction(boundingBoxInteraction)
                        }

                        $(map.getViewport()).toggleClass('drawing', isDrawing = true)
                        onDrawEnableListener && onDrawEnableListener()
                    },

                    disableDraw: function() {
                        map.removeInteraction(boundingBoxInteraction);
                        $(map.getViewport()).toggleClass('drawing', isDrawing = false)
                    },

                    /* spatial_lib implementation */

                    getPixelFromCoordinate: function(coords) {
                        return map.getPixelFromCoordinate(coords)
                    },

                    clearResults: function(geom) {
                        resultsBboxSource.clear()
                    },

                    addResultGeom: function(id, geojsonGeom, description) {
                        var f = new ol.Feature( {
                            geometry: spatial_lib.geojson2geom(geojsonGeom),
                            name: description,
                        })
                        f.setId(id)
                        resultsBboxSource.addFeature(f)
                    },

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
                            this.fitToExtent(updateExtent, 0.05)
                        }

                        selectionListener && selectionListener(geom)

                        if (this.coordinateInputs) {
                            for (var idx in this.coordinateInputs) this.coordinateInputs[idx].val(selectedExtent[idx].toFixed(5))
                        }
                    },
                    zoomIn: function() {
                        //TODO
                    },
                    reset: function() {
                        map.updateSize()
                        map.getView().setCenter(map.getView().constrainCenter(map.getView().getCenter()))
                    },
                    clearSelection: function() {
                        if (selectBoxSource) selectBoxSource.clear()
                    },
                    fitToExtent: function(extent, bufferRatio, addOnly) {
                        if (bufferRatio) {
                            var size = ol.extent.getSize(extent)
                            var extent = ol.extent.buffer(
                                extent,
                                    size[0] * size[1] == 0 ?
                                    0.1 :                     // for a Point : arbitrary 0.1deg buffer
                                    bufferRatio*(size[0] + size[1]) / 2   // Polygon : % of mean size
                            )
                        }
                        if (addOnly) extent = ol.extent.extend(extent, this.getExtent())
                        map.getView().fitExtent(extent, map.getSize())
                        map.getView().setCenter(map.getView().constrainCenter(map.getView().getCenter()))
                    },
                    fitToSelection: function() {
                        var extent = selectBoxSource.getExtent()
                        this.fitToExtent(extent, 0.05)
                    },
                    getSelection: function() {
                        return selectBoxSource.getFeatures()[0].getGeometry()
                    },
                    getExtent: function() {
                        return map.getView().calculateExtent(map.getSize())
                    }
                }

                boundingBoxInteraction.on('boxend', function (e) {
                    var newBox = boundingBoxInteraction.getGeometry()

                    mapComponent.setSelectedGeom(newBox, false)
                    mapComponent.disableDraw()
                })

                var selectButton = $("<div class='selectButton ol-unselectable ol-control ol-collapsed' style='top: 4em; left: .5em;'><button class='ol-has-tooltip' type='button'><span class='glyphicon icon-crop' aria-hidden='true'></span><span role='tooltip'>Draw Selection</span></button></div>")
                $(".ol-viewport").append(selectButton)
                selectButton.click(function (e) {
                    mapComponent.enableDraw()
                })

                return mapComponent
            }
        }

        return spatial_lib;
    } ()

})
