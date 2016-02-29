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

  if('ISSUE_ID' in window) {

    // Get count of comments
    $.ajax({
            url: '/comment/issue/count/'+window.ISSUE_ID,
            data: '',
            dataType: 'html',
            success: function(data, textStatus, xhr) {
               var count = parseInt(data, 10);
               var plural = "";
               if (count > 1) plural = "s";
               $('.comment_count').text(count + " comment" + plural);
            },
            error: function(xhr, status, exception) {
                $('.comment_count').text("");
            }
          });

    var url = '/comment/issue/get/'+window.ISSUE_ID+'?comments_per_page=999999';
    $.ajax({
            url: url,
            data: '',
            dataType: 'html',
            success: function(data, textStatus, xhr) {
              commentsSpinner.stop();
              $('#issue-comments-container').html(data);
              comments();
            },
            error: function(xhr, status, exception) {
              commentsSpinner.stop();
              $(spinDiv).hide();
              $('#comments .boxed')
                .append('Error loading comments: <code>'+url+'</code><br/><br/>')
                .append($('<pre>').text(JSON.stringify(exception)));
            }
          });
  }

});