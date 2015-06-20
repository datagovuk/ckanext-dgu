
var CKAN = CKAN || {};

CKAN.DguSpatialEditor = function($) {

    var COPYRIGHT_STATEMENTS =
        "Map background contains data from:<br/>" +
        "Ordnance Survey &copy; Crown copyright and database right [2012];<br/>" +
        "Royal Mail &copy; Royal Mail copyright and database right [2012];<br/>" +
        "Bathymetry by GEBCO &copy; Copyright [2012];<br/>" +
        "Land & Property Services (Northern Ireland) &copy; Crown copyright [2012]."

    var geojsonFormat = new ol.format.GeoJSON()
    var selectionListener //

    // Define British National Grid Proj4js projection (copied from http://epsg.io/27700.js)
    //proj4.defs("EPSG:27700","+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +towgs84=446.448,-125.157,542.06,0.15,0.247,0.842,-20.489 +units=m +no_defs");
    proj4.defs("EPSG:4258", "+title=ETRS89 +proj=longlat +ellps=GRS80 +no_defs");
    var EPSG_4326 = ol.proj.get('EPSG:4326');

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

    var activeLayer = OSLayers.INSPIRE_WGS84


    // Resolutions for the basemap to complement the OS layer
    var global_resolutions = [1.40625, 0.703125,0.3515625,0.17578125,0.0878906250,0.05]

    // take global resolutions above the OS layer supported resolutions to fill the gap
    var resolutions = []
    $.each(global_resolutions, function(idx, res) {
        if (res > activeLayer.resolutions[0]) resolutions.push(res)
    })
    resolutions = resolutions.concat(activeLayer.resolutions)

    var GAZETEER_PROJ = EPSG_4326
    var MAP_PROJ = ol.proj.get(activeLayer.projection)

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
        target: 'dataset-map',
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
            selectionLayer,
            activateLayer
        ],
        view: new ol.View({
            projection: MAP_PROJ,
            resolutions: resolutions,
            center: ol.proj.transform([-4.5, 54], EPSG_4326, MAP_PROJ),
            zoom: 0
        })
    });

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

        CKAN.DguSpatialEditor.setBBox(newBox, false)

        map.removeInteraction(boundingBoxInteraction);
        $(map.getViewport()).toggleClass('drawing', false)
    })

    var selectButton = $("<div class='selectButton ol-unselectable ol-control ol-collapsed' style='top: 4em; left: .5em;'><button class='ol-has-tooltip' type='button'><span class='glyphicon icon-crop' aria-hidden='true'></span><span role='tooltip'>Draw Selection</span></button></div>")
    $(".ol-viewport").append(selectButton)
    selectButton.click(function (e) {
        if (!$(this).hasClass('disabled')) {
            selectBoxSource.clear()
            map.addInteraction(boundingBoxInteraction)
            $(map.getViewport()).toggleClass('drawing', true)
        }
    })

    // important : this forces the refresh of the map when the tab is displayed. Short of that, the map is not displayed because the original offsetSize is null.
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        if (e.target.id == "section-geographic") {
            map.updateSize()
            var default_extent = [-13.69136, 49.90961, 1.77171, 60.84755]
            if (selectBoxSource.getFeatures().length)
                map.getView().fitExtent(selectBoxSource.getExtent(), map.getSize())
            else
                map.getView().fitExtent(default_extent, map.getSize())
        }

    })

    var currentQuery
    $('#spatial_name')
        .autocomplete({
            triggerSelectOnValidInput : false,
            minChars: 3,
            appendTo: '#gazetteer',
            showNoSuggestionNotice: true,
            preserveInput: true,
            serviceUrl: function(token) {
                return CKAN.DguSpatialEditor.geocoderServiceUrl + token + "*"},
            paramName: 'query',
            dataType: 'jsonp',
            noSuggestionNotice: '<i>No Results</i>',
            onSearchStart: function(params) {
                currentQuery = params['query']
                $("#spatial_spinner").show()
            },
            onSearchComplete: function(q, suggestions) {
                currentQuery = undefined
                $("#spatial_spinner").hide()
                // set min-width instead of width (list must be expandable to the right to allow for feature code display)
                $("div.autocomplete-suggestions").css({"min-width": $("#gazetteer input").outerWidth()});
            },
            onSearchError: function(q, jqXHR, textStatus, errorThrown) {
                if (q == currentQuery) // hide spinner only if the error is about the current query
                    $("#spatial_spinner").hide()
            },
            formatResult: function(suggestion, currentValue) {
                return "<div><div>"+suggestion.value+"</div><div>"+suggestion.data.properties.featuretype+"</div></div>"
            },

            transformResult: function(response) {
                return {
                    suggestions: $.map(response.features, function(feature) {
                        feature.bbox_geom = CKAN.DguSpatialEditor.bbox2geom(feature.bbox, GAZETEER_PROJ)
                        return { value: feature.properties.name, data: feature };
                    })
                };
            },
            onSelect: function (suggestion) {
                CKAN.DguSpatialEditor.selectSuggestion(suggestion)
            },
            onActivate: function(item) {
                CKAN.DguSpatialEditor.activateBBox(item.data.bbox_geom)
            }
        })
        .blur(function(e) {
            activateBoxSource.clear()
        })

    $('#use_exact_geom').change(function() {
        CKAN.DguSpatialEditor.setUseExactGeometry($(this).prop('checked'))
    })

    /*
    $('#use_pub_extent').change(function(evt) {
        CKAN.DguSpatialEditor.usePublisherExtent ($(this).prop('checked'))
    })
    */


    return {
        bbox2geom: function(bbox, bboxProjection) {
            if (!bbox) return undefined

            var e = ol.extent.boundingExtent([bbox.slice(0,2),bbox.slice(2,4)])
            // make sure the gazetteer extents are transformed into the system SRS
            if (bboxProjection) e = ol.proj.transformExtent(e, bboxProjection, MAP_PROJ)
            var size = ol.extent.getSize(e)
            // either a point or a box
            return size[0]*size[1] == 0 ?
                new ol.geom.Point(ol.extent.getCenter(e)) :
                new ol.geom.Polygon([[ol.extent.getBottomLeft(e), ol.extent.getTopLeft(e), ol.extent.getTopRight(e), ol.extent.getBottomRight(e)]])
        },

        regions: {
            "Worldwide": [-180, -90, 180, 90],
            "United Kingdom": [-13.69136, 49.90961, 1.77171, 60.84755],
            "Great Britain": [-6.23656, 49.96027, 1.77088, 58.67823],
            "British Isles": [-11.11705, 49.11890, 2.31459, 61.49506],
            "England & Wales": [-6.379880, 49.871159, 1.768960, 55.811741],
            "England": [-6.379880, 49.871159, 1.768960, 55.811741],
            "Scotland" : [-9.22987, 54.51334, -0.70514, 60.85988],
            "Wales" : [-5.81237, 51.32290, -2.64221, 53.45855],
            "Northern Ireland" : [-8.17384, 54.03422, -5.43013, 55.31105],
        },
        geocoderServiceUrl: 'http://unlock.edina.ac.uk/ws/search?minx=-20.48&miny=48.79&maxx=3.11&maxy=62.66&format=json&name=',
        currentSuggestion: null,
        useExactGeometry: false,
        coordinateInputs: null,

        setUseExactGeometry: function(bool) {
            if (this.useExactGeometry != bool) {
                this.useExactGeometry = bool
                this.selectSuggestion() // force geom refresh
            }
        },

        selectSuggestion: function(suggestion) {

            if (suggestion) {
                this.currentSuggestion = suggestion

                $("#spatial_name").val(this.currentSuggestion.value)
            }

            if (this.currentSuggestion) {
                if (this.currentSuggestion.data.properties.footprint && this.useExactGeometry) {
                    var _this = this
                    $.ajax(
                        {   dataType:"jsonp",
                            url:this.currentSuggestion.data.properties.footprint})
                    .done(
                        function (data) {
                            var geojson = data.footprints[0].geometry
                            var geom = _this.currentSuggestion.data.exactFootprint = geojsonFormat.readGeometry(geojson)
                            geom.transform(GAZETEER_PROJ, MAP_PROJ)
                            _this.setBBox(geom, true)
                        })
                } else {
                    this.setBBox(this.currentSuggestion.data.bbox_geom, true)
                }
            }
        },

        setBBox: function(geom, updateExtent) {
            selectBoxSource.clear()
            if (geom) {
                selectBoxSource.addFeature(new ol.Feature(geom))

                var selectedExtent = selectBoxSource.getExtent()

                if (updateExtent) {
                    var size = ol.extent.getSize(selectedExtent)
                    var bufferedExtent = ol.extent.buffer(
                        selectedExtent,
                            size[0] * size[1] == 0 ?
                            0.1 :                     // for a Point : arbitrary 0.1deg buffer
                            (size[0] + size[1]) / 20      // Polygon : 10% of mean size
                    )
                    map.getView().fitExtent(bufferedExtent, map.getSize())
                }

                selectionListener && selectionListener(JSON.stringify(geojsonFormat.writeGeometry(geom)))

                if (this.coordinateInputs) {
                    for (var idx in this.coordinateInputs) this.coordinateInputs[idx].val(selectedExtent[idx].toFixed(5))
                }
            } else {
                selectionListener && selectionListener()
                if (this.coordinateInputs) {
                    for (var idx in this.coordinateInputs) this.coordinateInputs[idx].val("")
                }
            }
        },

        activateBBox: function(geom) {
            activateBoxSource.clear()
            activateBoxSource.addFeature(new ol.Feature(geom ))
        },

        onBBox: function(listener) {
            selectionListener = listener
        },

        bindCoordinateInputs: function(minxInput, minyInput, maxxInput, maxyInput) {
            this.coordinateInputs = [
                $(minxInput),
                $(minyInput),
                $(maxxInput),
                $(maxyInput)
            ]
             var _this = this
            this.coordinateInputs.forEach(function(input) {
                input.change(function() {
                    _this.syncWithInputCoordinates()
                })})
        },

        syncWithInputCoordinates: function() {
            this.setBBox(this.bbox2geom(this.coordinateInputs.map(function(input) {return parseFloat(input.val())})))
        },

        bindInput: function(el) {
            var $el = $(el)
            if ($el.val()) try { CKAN.DguSpatialEditor.setBBox(geojsonFormat.readGeometry($el.val()), true) } catch (err) {}
            $el.prop('disabled', $el.val() == false)  // disable the input field if no value to avoid server-side validation failure
            CKAN.DguSpatialEditor.onBBox(function(bbox) {
                $el.prop('disabled', !bbox || bbox === undefined)
                $el.val(bbox || "")
            })
        },

        usePublisherExtent: function(toggle) {
            if (typeof(publishers) != "undefined" && toggle) {
                var publisher
                $.each(publishers, function(name, pub) {
                    if (pub && pub.id == $("#owner_org").val())
                        publisher = pub
                })
                var bbox = publisher && publisher.spatial
                var spatial_name = publisher && publisher.spatial_name
                if (bbox)
                    try {
                        CKAN.DguSpatialEditor.setBBox(geojsonFormat.readGeometry(bbox), true)
                    } catch (err) {}

                if (spatial_name)
                    $("#spatial_name").val(spatial_name)

                $("#spatial_name").prop("readonly", true);
                $("input[id^=bbox_]").prop('readonly', true)
                $("div.selectButton").toggleClass('disabled', true)
                $("#region-select>a.btn:not(.btn-publisherselect)").toggleClass('disabled', true)
                $(".btn-publisherselect").toggleClass("selected", true)
                $('#spatial_name').autocomplete().disable()
            } else {
                $("#spatial_name").prop('readonly', false)
                $("input[id^=bbox_]").prop('readonly', false)
                $("div.selectButton").toggleClass('disabled', false)
                $("#region-select>a.btn:not(.btn-publisherselect)").toggleClass('disabled', false)
                $(".btn-publisherselect").toggleClass("selected", false)
                $('#spatial_name').autocomplete().enable()
            }
            $('#use_pub_extent').prop('checked', toggle)
        }
    }
} (jQuery)

$(function() {
    CKAN.DguSpatialEditor.bindCoordinateInputs("#bbox_minx","#bbox_miny","#bbox_maxx","#bbox_maxy")
    CKAN.DguSpatialEditor.bindInput("#spatial")

    if ($('#use_pub_extent').length) {
        $("#region-select")
            .append(
            $("<a class='btn btn-publisherselect' role='button'>Use Publisher Extent</a>")
                .click(function() {
                    CKAN.DguSpatialEditor.usePublisherExtent(!$('#use_pub_extent').prop('checked'))
                })
                .append(
                $('#use_pub_extent').click(function(evt) {
                    $('#use_pub_extent').prop('checked', !$('#use_pub_extent').prop('checked'))
                    CKAN.DguSpatialEditor.usePublisherExtent(!$('#use_pub_extent').prop('checked'))
                    evt.stopPropagation()
                })
            )
        )
    }

    $("#region-select")
        .append(
        $("<a class='btn btn-warning' role='button'>None</a>")
            .click(function() {
                if (!$(this).hasClass('disabled')) {
                    CKAN.DguSpatialEditor.setBBox()
                    $("#spatial_name").val("")
                }
            }))
    $.each(CKAN.DguSpatialEditor.regions, function(name, box) {

        $("#region-select")
            .append(
        $("<a class='btn btn-info' role='button'>"+name.replace(" ", "&nbsp;")+"</a>")
                .click(function() {
                    if (!$(this).hasClass('disabled')) {
                        CKAN.DguSpatialEditor.setBBox(CKAN.DguSpatialEditor.bbox2geom(box), true)
                        $("#spatial_name").val(box ? name : "")
                    }
                })
        )
        /*
        $("#region-select")
            .append($("<option value='"+box+"'>"+name+"</option>"))
            .change(function(e) {
                var optionSelected = $("option:selected", this);
                var valueSelected = this.value;
            })
            */
    })

    CKAN.DguSpatialEditor.usePublisherExtent ($('#use_pub_extent').prop('checked'))
})
