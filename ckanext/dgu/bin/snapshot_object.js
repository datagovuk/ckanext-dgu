#!/usr/bin/env phantomjs

/*
 * Rasterizes page content for use in IE7 fallback scripts (eg. capturing D3 visualisations).
 * Execute: phantomjs rasterize_ie7_content.js
 *
 * Usage: ./snapshot_object.js $URL $OBJECT1 $IMAGE1 $OBJECT2 $IMAGE2...
 *    eg. ./snapshot_object.js http://localhost:3008/data/viz/social_investment_and_foundations.js social_investment_totals ../theme/src/images/social_investment_totals.png
 * Alternatively: Use my sister script, snapshot_all.js
 *
 * --
 * Note: This generates raw images. You need to run `grunt images` afterward to push them
 * through the content pipeline.
 * --
 * Note: The local webserver must be running. I assume it's on localhost:3008
 */

var system = require('system');
var url = system.args[1];
var objectsToSnapshot = [];
for (var i=2;i<system.args.length;i+=2) {
  var objectId = system.args[i];
  var image = system.args[i+1];
  objectsToSnapshot.push({objectId:objectId,image:image})
}

var page = require('webpage').create();
page.viewportSize = { width: 1024, height: 1 };
page.open(url, function(status) {
    if (status!=='success') {
        console.err('Unable to load '+url);
        phantom.exit();
    }
    else {
        window.setTimeout(function() {
            for (var i=0;i<objectsToSnapshot.length;i++) {
              var objectId = objectsToSnapshot[i].objectId;
              var image = objectsToSnapshot[i].image;
              var boundingRect = page.evaluate( "function() { return document.getElementById('"+objectId+"').getBoundingClientRect(); }");
              page.clipRect = boundingRect;
              page.render(image);
              console.log('---------');
              console.log('Successfully rendered: '+image);
            }
            phantom.exit();
        }, 1000);
    }
});
