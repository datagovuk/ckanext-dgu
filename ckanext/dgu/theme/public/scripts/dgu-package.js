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

  // Attach tooltips to .hover-text containing lots of text
  var MAX_LENGTH = 60;
  var hoverText = $('.hover-text');
  $.each(hoverText, function(i, element) {
    element = $(element);
    var too_long = element.text().length > MAX_LENGTH;
    if (too_long) {
      element.tooltip( { 
        title: element.text(),
        placement: 'top'
      });
    }
  });

  // Create a spinner in the comments loader
  var spinDiv = $('.comments-spinner')[0];
  var commentsSpinner = new Spinner(spinConfig).spin(spinDiv);

  var url = '/comment/get/'+DATASET_ID;
  $.ajax({
          url: url,
          data: '',
          dataType: 'html',
          success: function(data, textStatus, xhr) {
            commentsSpinner.stop();
            $('#comments-container').html(data);
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
