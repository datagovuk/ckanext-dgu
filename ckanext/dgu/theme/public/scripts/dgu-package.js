$(function() {
  var spinConfig = {
    lines: 9, // The number of lines to draw
    length: 5, // The length of each line
    width: 2, // The line thickness
    radius: 6, // The radius of the inner circle
    rotate: 3, // The rotation offset
    color: '#777', // #rgb or #rrggbb
    speed: 2.1, // Rounds per second
    trail: 43, // Afterglow percentage
    shadow: false, // Whether to render a shadow
    hwaccel: false, // Whether to use hardware acceleration
    className: 'spinner', // The CSS class to assign to the spinner
    zIndex: 2e9, // The z-index (defaults to 2000000000)
    top: 'auto', // Top position relative to parent in px
    left: 'auto' // Left position relative to parent in px
  };

  // Create a spinner in the comments loader
  var spinDiv = $('.comments-spinner')[0];
  var commentsSpinner = new Spinner(spinConfig).spin(spinDiv);

  var contortDrupal = function(data) {
    data = data || '<div class="boxed"><h2>Comments</h2>(no data)</div>';
    var dom = $(data);
    if (dom.find('#comments').length==0) {
        /* Push the entire thing inside a #comments div */
        dom = $('<div id="comments" />').append(dom);
    }
    if (dom.find('.new-comment-link').length==0) {
        var button = dom.find('#comment-add').remove();
        dom.prepend( $('<div class="new-comment-link"/>').append(button) );
    }
    dom.find('#comment-add').addClass('btn').addClass('btn-primary').css({'float':'right'});
    dom.find('.comment').addClass('boxed');
    dom.find('ul.links a').addClass('btn').addClass('btn-primary');
    dom.find('.comment-content h3 a').each(function(i, el) {
      el = $(el);
      var link = el.attr('href');
      link = link.substr( link.indexOf('#') );
      el.attr('href',link);
    });
    return dom;
  };

  var url = '/comment/get/'+DATASET_ID;
  $.ajax({
          url: url,
          data: '',
          dataType: 'html',
          success: function(data, textStatus, xhr) {
            commentsSpinner.stop();
            $('#comments-container').html(contortDrupal(data));
          },
          error: function(xhr, status, exception) {
            commentsSpinner.stop();
            $(spinDiv).hide();
            $('#comments .boxed')
              .append('Error loading comments: <code>'+url+'</code><br/><br/>')
              .append($('<pre>').text(JSON.stringify(exception)));
          }
        });
});
