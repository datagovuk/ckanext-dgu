#!/usr/bin/env node 

var webshot = require('webshot');

/*
 * Create rasterized fallbacks of graph pages.
 * Used for IE7 fallback pages.
 */
var targets = [
{
  url: 'http://localhost:2008/data/viz/social-investment-and-foundations',
  dest: 'src/images/graph-socialinvestment.png',
}
];

// ------------
//

for (var i=0;i<targets.length;i++) {
  var t = targets[i];
  var options = {
    renderDelay: 2000,
    windowSize: {width:1200,height:768},
    shotSize: {width:940,height:2650},
    shotOffset: {
      top: 240,
      bottom: 200,
      left: 130, 
    }
  };
  webshot(t.url,
      t.dest,
      options,
      function(err) {}
  );
}
