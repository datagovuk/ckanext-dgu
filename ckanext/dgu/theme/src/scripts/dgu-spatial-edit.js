
var CKAN = CKAN || {};

CKAN.DguSpatialEditor = function($) {

    var geojsonFormat = new ol.format.GeoJSON()
    var selectionListener //

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


    var map = new ol.Map({
        target: 'map',
        size: [400,300],
        layers: [
            new ol.layer.Tile({
                source: new ol.source.TileWMS({
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
        selectBoxSource.addFeature(new ol.Feature(newBox))
        map.removeInteraction(boundingBoxInteraction);
        selectionListener && selectionListener(JSON.stringify(geojsonFormat.writeGeometry(newBox)))
    })

    var selectButton = $("<div class='selectButton ol-unselectable ol-control ol-collapsed' style='top: 4em; left: .5em;'><button class='ol-has-tooltip' type='button'><span>[]</span><span role='tooltip'>Draw Selection</span></button></div>")
    $(".ol-viewport").append(selectButton)
    selectButton.click(function (e) {
        selectBoxSource.clear()
        map.addInteraction(boundingBoxInteraction)
    })

    // important : this forces the refresh of the map when the tab is displayed. Short of that, the map is not displayed because the original offsetSize is null.
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        if (e.target.id == "section-geographic") {
            map.updateSize()
            map.getView().fitExtent(selectBoxSource.getExtent(), map.getSize())
        }

    })

    function bbox2geom(bbox) {
        var e = ol.extent.boundingExtent([bbox.slice(0,2),bbox.slice(2,4)])
        // make sure the gazetteer extents are transformed into the system SRS
        e = ol.proj.transformExtent(e, GAZETEER_PROJ, EPSG_4258)
        var size = ol.extent.getSize(e)
        // either a point or a box
        return geom = size[0]*size[1] == 0 ?
            new ol.geom.Point(ol.extent.getCenter(e)) :
            new ol.geom.Polygon([[ol.extent.getBottomLeft(e), ol.extent.getTopLeft(e), ol.extent.getTopRight(e), ol.extent.getBottomRight(e)]])
    }

    $('#spatial_name')
        .autocomplete({
            triggerSelectOnValidInput : false,
            minChars: 3,
            preserveInput: true,
            serviceUrl: function(token) {
                return CKAN.DguSpatialEditor.geocoderServiceUrl + token + "*"},
            //paramName: 'name',
            dataType: 'jsonp',
            onSearchStart: function() {$("#spatial_spinner").show()},
            onSearchComplete: function() {$("#spatial_spinner").hide()},
            onSearchError: function() {$("#spatial_spinner").hide()},
            transformResult: function(response) {
                return {
                    suggestions: $.map(response.features, function(feature) {
                        feature.bbox_geom = bbox2geom(feature.bbox)
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

    return {
        geocoderServiceUrl: 'http://unlock.edina.ac.uk/ws/search?minx=-20.48&miny=48.79&maxx=3.11&maxy=62.66&format=json&name=',
        currentSuggestion: null,
        useExactGeometry: false,

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
                            geom.transform(GAZETEER_PROJ, EPSG_4258)
                            _this.setBBox(geom)
                            selectionListener && selectionListener(JSON.stringify(geojsonFormat.writeGeometry(geom)))
                        })
                } else {
                    this.setBBox(this.currentSuggestion.data.bbox_geom)
                    selectionListener && selectionListener(JSON.stringify(geojsonFormat.writeGeometry(this.currentSuggestion.data.bbox_geom)))
                }
            }
        },

        setBBox: function(geom) {
            selectBoxSource.clear()
            selectBoxSource.addFeature(new ol.Feature(geom ))
            var size = ol.extent.getSize(selectBoxSource.getExtent())
            var bufferedExtent = ol.extent.buffer(
                selectBoxSource.getExtent(),
                size[0]*size[1] == 0 ?
                    0.1 :                     // for a Point : arbitrary 0.1deg buffer
                    (size[0]+size[1])/20      // Polygon : 10% of mean size
                )
            map.getView().fitExtent(bufferedExtent, map.getSize())
        },

        activateBBox: function(geom) {
            activateBoxSource.clear()
            activateBoxSource.addFeature(new ol.Feature(geom ))
        },

        onBBox: function(listener) {
            selectionListener = listener
        },

        bindInput: function(el) {
            var $el = $(el)
            CKAN.DguSpatialEditor.setBBox(geojsonFormat.readGeometry($el.val()))
            CKAN.DguSpatialEditor.onBBox(function(bbox) {
                $el.val(bbox)
            })
        }
    }
} (jQuery)