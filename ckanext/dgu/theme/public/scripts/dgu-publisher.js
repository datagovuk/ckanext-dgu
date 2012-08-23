$(function() {
  var jstree = $("#publisher-tree").jstree(
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

  jstree.delegate('a', 'click', function(e){ window.location.href=$(this).attr('href'); });

  jstree.bind('loaded.jstree', function() { 
    var li = $('.jstree li');
    var active = $( $('.jstree li strong').parents('li')[0] );
    // Hide almost everything
    var hidden = false;
    if (li.length >15) {
      $.each(li, function(i, element) {
        element=$(element);
        if (element[0]!=active[0] && element.hasClass('jstree-leaf')) {
          $(element).hide();
          hidden = true;
        }
      });
    }

    if (hidden) {
      var treeButton = $('#publisher-tree-expand');
      treeButton.show();
      treeButton.click(function() {
        treeButton.hide();
        $.each(li, function(i,element) { $(element).show(); });
      });
    }
  });

});

