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

  var input = $('#dataset-search #q');
  var url = '/api/2/search/dataset';

  var pollApi = function(typeahead,query) {
    $.ajax({
      url: url, 
      data: { fl: 'title', q: query }, 
      success: function (data) {
        var array = data.results;
        var out = [];
        var i=0;
        while (!(i==array.length)) {
          out.push(array[i++].title);
        }
        typeahead.process(out);
        SearchSpinner.stop();
      }
    });
  };

  var runningTimeout = null;

  var sourceFunction = function (typeahead, query) {
    if (runningTimeout) {
      clearTimeout(runningTimeout);
      runningTimeout = null;
    }
    if (!query) {
      SearchSpinner.stop();
      return [];
    }
    SearchSpinner.start();
    runningTimeout = setTimeout(function() { pollApi(typeahead,query); }, 200);
  };

  input.typeahead({
    source: sourceFunction
  });

});
