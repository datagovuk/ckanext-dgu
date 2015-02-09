
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
            default_extent: [[90, 180], [-90, -180]]
        }
    }

    var initCallbacks = []
    DguSearch.onReady = function(callback) {
        initCallbacks.push(callback)
    }
    DguSearch.prototype = {

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
            $(['ext_bbox', 'ext_prev_extent']).each(function(index, item){
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

        var spatial_lib = {

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

                $(inputEl)
                    .autocomplete({
                        triggerSelectOnValidInput : false,
                        minChars: 3,
                        appendTo: '#gazetteer',
                        preserveInput: true,
                        serviceUrl: function(token) {
                            return geocoderServiceUrl + token + "*"},
                        //paramName: 'name',
                        dataType: 'jsonp',
                        onSearchStart: function() {
                            spinner.show()
                        },
                        onSearchComplete: function() {
                            spinner.hide()
                        },
                        onSearchError: function() {
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
                var resultsStroke = new ol.style.Stroke({color: 'rgba(139,198,58, 0.6)',width: 1})
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
                        resultsLayer,
                        suggestionLayer
                    ],
                    view: new ol.View({
                        projection: EPSG_4258,
                        resolutions: resolutions,
                        center: [-4.5, 54],
                        zoom: 0
                    })
                });

                var resultsOverlay = new ol.FeatureOverlay({
                    map: map,
                    style: (function() {
                        var stroke = new ol.style.Stroke({color: '#8bc658', width: 2.5})
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
                map.getView().constrainCenter = function(center) {
                    var resolution = this.getResolution()
                    if (center !== undefined && resolution !== undefined) {
                        var mapSize = /** @type {ol.Size} */ (map.getSize());
                        var viewResolution = resolution;
                        var mapHalfWidth = (mapSize[0] * viewResolution) / 2.0;
                        var mapHalfHeight = (mapSize[1] * viewResolution) / 2.0;
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
                    if (!isDrawing) {
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
