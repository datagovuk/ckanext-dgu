$(function() {
  // Truncate long .notes elements
  var notes = $('.notes');
  notes.dotdotdot({
    height: 230,
    tolerance: 10,
    after: 'a.notes-read-more'
  });
  notes.trigger('isTruncated', function(isTruncated) {
    if (!isTruncated) {
      notes.find('a.notes-read-more').remove();
    }
    else {
      var more = notes.find('a.notes-read-more');
      more.css('display', 'block');
      more.click(function(e) {
        e.preventDefault();
        $('.notes').trigger('destroy.dot');
        notes.find('a.notes-read-more').remove();
        return false;
      });
    }
  });

  var license_info = $('#license-info');
  var more = license_info.find('a.license-read-more');
  more.show()
  license_info.dotdotdot({
    height: 50,
    tolerance: 10,
    after: 'a.license-read-more'
  });
  license_info.trigger('isTruncated', function(isTruncated) {
    if (!isTruncated) {
      license_info.find('a.license-read-more').remove();
    }
    else {
      var more = license_info.find('a.license-read-more');
      more.click(function(e) {
        e.preventDefault();
        $('#license-info').trigger('destroy.dot');
        license_info.find('a.license-read-more').remove();
        return false;
      });
    }
  });

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

  var url = '/comment/get/'+window.DATASET_ID+'?comments_per_page=999999';
  $.ajax({
          url: url,
          data: '',
          dataType: 'html',
          success: function(data, textStatus, xhr) {
            commentsSpinner.stop();
            $('#comments-container').html(data);
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

  // Year segmentation
  $(".year .year_items").hide();
  $(".year .year_items").first().show();

  // 'View More' and 'View Less' are hidden by default so
  // that viewers without javascript cannot see them

  // Show the first 'View Less' button
  $(".year .hideyear").first().show();


  // Show all but the first 'View More' button
  $(".year .showyear").show();
  $(".year .showyear").first().hide();

  $(".year h3 span.showyear").on('click', function(){
    $(this).parent().next('.year_items').fadeIn();
    $(this).siblings('.hideyear').show();
    $(this).hide();
    return false;
  });
  $(".year h3 span.hideyear").on('click', function(){
    $(this).parent().next('.year_items').fadeOut();
    $(this).siblings('.showyear').show();
    $(this).hide();
    return false;
  });

 // Closed issues
  $(".hide-closed-issues").hide();
  $("#issue-list-closed").hide();
  $("span.show-closed-issues").on('click', function(){
    $(this).parent().next('.issue-list-group').fadeIn();
    $(this).siblings('.hide-closed-issues').show();
    $(this).hide();
    return false;
  });
  $("span.hide-closed-issues").on('click', function(){
    $(this).parent().next('.issue-list-group').fadeOut();
    $(this).siblings('.show-closed-issues').show();
    $(this).hide();
    return false;
  });


});


