#!/usr/bin/env node 

var webshot = require('webshot');

/*
 * Create rasterized fallbacks of graph pages.
 * Used for IE7 fallback pages.
 */
var targets = [
{
  url        : 'http://localhost:3008/data/viz/social-investment-and-foundations',
  dest       : 'src/images/graph-socialinvestment.png',
  shotHeight : 2650,
  renderDelay: 2000,
},
{
  url       : 'http://localhost:3008/data/viz/investment-readiness-programme',
  dest      : 'src/images/graph-investmentreadiness.png',
  shotHeight: 1280,
}
];


// ------------
//
for (var i=0;i<targets.length;i++) {
  var t = targets[i];
  /* Fill out target default options */
  if (typeof(t.renderDelay)==='undefined') {
    t.renderDelay = 0; // No intro animation
  }
  if (typeof(t.windowWidth)==='undefined') {
    t.windowWidth = 1024; // Expected screen size
  }
  if (typeof(t.shotWidth)==='undefined') {
    t.shotWidth = 940; // No intro animation
  }
  if (typeof(t.shotOffsetTop)==='undefined') {
    t.shotOffsetTop = 140; // Standard header space
  }
  if (typeof(t.shotOffsetLeft)==='undefined') {
    t.shotOffsetLeft = (t.windowWidth-t.shotWidth)/2; // Centered
  }
  var options = {
    renderDelay: t.renderDelay,
    windowSize: {
      width:t.windowWidth,
      height:99 /* Immaterial */
    },
    shotSize: {
      width:t.shotWidth,
      height:t.shotHeight
    },
    shotOffset: {
      top:t.shotOffsetTop,
      left: t.shotOffsetLeft,
    }
  };
  webshot(t.url, t.dest, options, function(err) {});
}

