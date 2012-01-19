(function ($) {
  $(document).ready(function () {

    /* URL auto-completion */
    var isDatasetNew = $('body.package.new').length > 0;
    if (true || isDatasetNew) {
      // Set up magic URL slug editor
      CKAN.Dgu.setupUrlEditor('package', false);
      $("#title").focus();
    }

  });
}(jQuery));

var CKAN = CKAN || {};

CKAN.Dgu = function($, my) {

  my.bindInputChanges = function(input, callback) {
    input.keyup(callback);
    input.keydown(callback);
    input.keypress(callback);
    input.change(callback);
  };

  my.setupUrlEditor = function(slugType,readOnly) {
    // Page elements to hook onto
    var titleInput = $('.js-title');
    var urlText = $('.js-url-text');
    var urlSuffix = $('.js-url-suffix');
    var urlInput = $('.js-url-input');
    var validMsg = $('.js-url-is-valid');

    if (titleInput.length==0) throw "No titleInput found.";
    if (urlText.length==0) throw "No urlText found.";
    if (urlSuffix.length==0) throw "No urlSuffix found.";
    if (urlInput.length==0) throw "No urlInput found.";
    if (validMsg.length==0) throw "No validMsg found.";

    var api_url = '/api/2/util/is_slug_valid';
    // (make length less than max, in case we need a few for '_' chars to de-clash slugs.)
    var MAX_SLUG_LENGTH = 90;

    var titleChanged = function() {
      var lastTitle = "";
      var regexToHyphen = [ new RegExp('[ .:/_]', 'g'), 
                        new RegExp('[^a-zA-Z0-9-_]', 'g'), 
                        new RegExp('-+', 'g')];
      var regexToDelete = [ new RegExp('^-*', 'g'), 
                        new RegExp('-*$', 'g')];

      var titleToSlug = function(title) {
        var slug = title;
        $.each(regexToHyphen, function(idx,regex) { slug = slug.replace(regex, '-'); });
        $.each(regexToDelete, function(idx,regex) { slug = slug.replace(regex, ''); });
        slug = slug.toLowerCase();

        if (slug.length<MAX_SLUG_LENGTH) {
            slug=slug.substring(0,MAX_SLUG_LENGTH);
        }
        return slug;
      };

      // Called when the title changes
      return function() {
        var title = titleInput.val();
        if (title == lastTitle) return;
        lastTitle = title;

        slug = titleToSlug(title);
        urlInput.val(slug);
        urlInput.change();
      };
    }();

    var urlChanged = function() {
      var timer = null;

      var checkSlugValid = function(slug) {
        $.ajax({
          url: api_url,
          data: 'type='+slugType+'&slug=' + slug,
          dataType: 'jsonp',
          type: 'get',
          jsonpCallback: 'callback',
          success: function (data) {
            if (data.valid) {
              validMsg.html('<span style="font-weight: bold; color: #0c0">This URL is available!</span>');
            } else {
              validMsg.html('<span style="font-weight: bold; color: #c00">This URL is not available!</span>');
            }
          }
        });
      }

      return function() {
        slug = urlInput.val();
        urlSuffix.html('<span>'+slug+'</span>');
        if (timer) clearTimeout(timer);
        if (slug.length<2) {
          validMsg.html('<span style="font-weight: bold; color: #444;">Type at least two characters...</span>');
        }
        else {
          validMsg.html('<span style="color: #777;">Checking...</span>');
          timer = setTimeout(function () {
            checkSlugValid(slug);
          }, 200);
        }
      };
    }();

    if (readOnly) {
      slug = urlInput.val();
      urlSuffix.html('<span>'+slug+'</span>');
    }
    else {
      var editLink = $('.js-url-editlink');
      editLink.show();
      // Hook title changes to the input box
      my.bindInputChanges(titleInput, titleChanged);
      my.bindInputChanges(urlInput, urlChanged);
      // Set up the form
      urlChanged();

      editLink.live('click',function(e) {
        e.preventDefault();
        $('.js-url-viewmode').hide();
        $('.js-url-editmode').show();
        urlInput.select();
        urlInput.focus();
      });
    }
  }

  return my;
}(jQuery, CKAN.Dgu || {});
