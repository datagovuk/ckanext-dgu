$(function() {
  var jstree = $("#publisher-tree");

  jstree.delegate('a', 'click', function(e){ window.location.href=$(this).attr('href'); });

  jstree.bind('loaded.jstree', function() { 
    var li = $('.jstree li');
    var active = $( $('.jstree li strong').parents('li')[0] );
    var activeIndex = li.index(active);

    var max = 15;
    if (li.length>15) {
      var treeWrapper = $('#publisher-tree-wrapper');
      var treeButton = $('#publisher-tree-expand');
      var hideAfter = 
      $.each(li, function(i, element) {
        if (i>=activeIndex) $(element).hide();
      });
      treeButton.show();
      treeButton.click(function() {
        treeButton.hide();
        $.each(li, function(i,element) { $(element).show(); });
      });
    }
  });
  jstree.bind('open_node.jstree', function(e) {
    $('.jstree-open').show();
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

