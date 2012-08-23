$(function() {
  var jstree = $("#publisher-tree");

  jstree.delegate('a', 'click', function(e){ window.location.href=$(this).attr('href'); });

  jstree.bind('loaded.jstree', function() { 
    var li = $('.jstree li');
    var active = $( $('.jstree li strong').parents('li')[0] );
    var offset = Math.max(0, active.offset().top - jstree.offset().top - 20);
    jstree.scrollTop(offset);
  });

  jstree.jstree(
     {
      "themes" : {
          "icons" : false
      },
      "plugins" : ["themes","html_data","ui"],
      "core": {
          "load_open" : true,
          "initially_open" : [PUBLISHER_PARENT, PUBLISHER_GROUP]
      }
     }
    );

});

