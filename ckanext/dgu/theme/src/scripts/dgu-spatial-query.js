
$(function() {
    //var spatialModule = window.ckan.module.instances['spatial-query']

    window.ckan.DGU.SearchModule.onReady(function(module) {
        $("[data-bbox]").each(function( idx, el ) {
            var id = $(el).attr('data-id')
            module.map.addResultGeom(id, $(el).attr('data-bbox'), $(el).attr('data-title'))
            $(el).hover(
                function() {module.map.highlightResult(id)},
                function() {module.map.highlightResult()}
            )
            module.map.fitToResults();
        })

        module.spatial_lib.createGazetteerInput(
            "#gazetteer>input",
            function(selection) {
                var extent = selection.data.bbox_geom.extent
                var size = ol.extent.getSize(extent)
                var geom
                if (size[0] * size[1] == 0) {
                    // selection is a Point --> buffer it
                    extent = ol.extent.buffer(selection.data.bbox_geom.extent, 0.005)  // arbitrary 0.1 deg buffer
                    geom = new ol.geom.Polygon([[ol.extent.getBottomLeft(extent), ol.extent.getTopLeft(extent), ol.extent.getTopRight(extent), ol.extent.getBottomRight(extent)]])
                } else {
                    geom = selection.data.bbox_geom
                }
                module.map.setSelectedGeom(geom);

                module.submitForm()
            },
            function(hovered) {
                module.map.highlightGeom(hovered);
            }
        )
    })
})