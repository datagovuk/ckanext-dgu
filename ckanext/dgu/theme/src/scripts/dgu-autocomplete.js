$(function() {
  // Singleton object to handle spinner animation. Call start() and stop()
  var SearchSpinner = {
    el: $('.search-spinner')[0],
    config: {
      lines: 9, // The number of lines to draw
      length: 4, // The length of each line
      width: 2, // The line thickness
      radius: 3, // The radius of the inner circle
      rotate: 0, // The rotation offset
      color: '#000', // #rgb or #rrggbb
      speed: 2, // Rounds per second
      trail: 60, // Afterglow percentage
      shadow: false, // Whether to render a shadow
      hwaccel: false, // Whether to use hardware acceleration
      className: 'spinner', // The CSS class to assign to the spinner
      zIndex: 2e9, // The z-index (defaults to 2000000000)
      top: 'auto', // Top position relative to parent in px
      left: 'auto' // Left position relative to parent in px
    },
    active: null,
    start: function() {
      if (this.active) return;
      this.active = new Spinner(this.config).spin(this.el);
    },
    stop: function() {
      if (!this.active) return;
      this.active.stop();
      this.active = null;
    }
  };

  var url = '/api/2/search/dataset';

  var pollApi = function(request,response) {
    $.ajax({
      url: url, 
      data: { fl: 'title', q: request.term }, 
      success: function (data) {
        var array = data.results;
        var out = [];
        var i=0;
        while (!(i==array.length)) {
          out.push(array[i++].title);
        }
        response(out);
        SearchSpinner.stop();
      }
    });
  };

  // Allow only one timeout callback at a time
  var timer = null;

  // Called when the user types in the search box
  var sourceFunction = function (request, response) {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    if (!request) {
      SearchSpinner.stop();
      response([]);
    }
    SearchSpinner.start();
    // Don't poll the API immediately. Spam crazy!
    timer = setTimeout(function() { pollApi(request,response); }, 200);
  };
  var onSelect = function(e) {
    var trigger = $(e.target);
    if (trigger.is('a')) {
      // Mouse has clicked an autocomplete element.
      // It has not yet been written to the input
      $('#dataset-search #q').val(trigger.html());
    }
    else {
      // Keyboard has selected an autocomplete element.
      // It has already been written to the input.
      //  DAMN YOU JQUERY UI!
    }
    $('form#dataset-search').submit();
  }

  // Attach jQueryUI autocomplete function to the input textbox
  $('#dataset-search #q').autocomplete({
    source: sourceFunction,
    minLength: 2,
    select: onSelect
  });

});
