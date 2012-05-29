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
    var max = 2;
    if (li.length>max) {
      var treeWrapper = $('#publisher-tree-wrapper');
      var treeButton = $('#publisher-tree-expand');
      $.each(li, function(i, element) {
        if (i>=max) $(element).hide();
      });
      treeButton.show();
      treeButton.click(function() {
        treeButton.hide();
        $.each(li, function(i,element) { $(element).show(); });
      });
    }
  });

});

