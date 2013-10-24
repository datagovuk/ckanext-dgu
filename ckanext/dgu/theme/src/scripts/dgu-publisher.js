$(function() {
  // Hack JSTree to prevent it adding stylesheets (we manage these ourselves)
  $.vakata.css.add_sheet = function(){};

  var jstree = $("#publisher-tree");
  assert(jstree.length,'Bad DOM');

  jstree.delegate('a', 'click', function(e){ window.location.href=$(this).attr('href'); });

  jstree.one('reselect.jstree', function() { 
    var li = $('.jstree li');
    var active = $( $('.jstree li strong').parents('li')[0] );
    var offset = Math.max(0, active.offset().top - jstree.offset().top - 80);
    jstree.scrollTop(offset);
  });

  jstree.jstree(
     {
     "theme_name": false,
      "themes" : {
          "icons" : false
      },
      "plugins" : ["themes","html_data","ui"],
      "core": {
          "load_open" : true,
          "initially_open" : [window.dgu_publisher_hierarchy_parent, window.dgu_publisher_hierarchy_this ],
      }
     }
    );

  jstree.bind('loaded.jstree', function() {
    jstree.find('li a').each( function(i, el) {
      el = $(el);
      if (el.text().length > 32) {
        el.tooltip({
          title: '"'+$.trim(el.text())+'"',
          placement: 'left'
        });
      }
    });
  });
});

