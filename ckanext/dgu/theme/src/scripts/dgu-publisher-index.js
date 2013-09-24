function publisher_search() {
  var term = $("#q").val(); var url = CKAN.SITE_URL + '/api/2/util/group/autocomplete?type=organization&amp;q=' + escape(term);

  $("#search_results").html('<h4>Results:</h4>');
  $("#search_results").css("display", "block");
  $.getJSON(url, function(data) {

    $(".result-count").html(data.length);
    $(".result-count, .result-count-footer").css('color','#000');
    $.each(data, function(idx, groupobj) {
      var tpl = '<tr><td>' +
                '<a href="/publisher/' + groupobj.name + '">' + groupobj.title +
                '</a></td></tr>';
      $("#search_results").append( tpl );
    });
  });
  $('#q').autocomplete('close');
  return false;
}

$(function() {
  // Hack JSTree to prevent it adding stylesheets (we manage these ourselves)
  $.vakata.css.add_sheet = function(){};

  $('#publisher-search').bind('submit',function(e) {
    if (e.preventDefault) e.preventDefault();
    publisher_search();
  });

  $('a[data-toggle="tab"]').on('shown', function (e) {
    if (e.target.hash == '#publishersearch') {
      $("#q").focus();
    };
  });

  $("#publisher-tree").jstree( {
   "themes" : {
     "icons" : false
    },
   "plugins" : ["themes","html_data","ui"]}
  ).delegate('a', 'click', function(e){ window.location.href=$(this).attr('href'); });

  $('#q').autocomplete({
    source: window.dgu_publisher_autocomplete,
    minLength: 1,
    select: function() { $('#publisher-search').submit();  }
  });
});

