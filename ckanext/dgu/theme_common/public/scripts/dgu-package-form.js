(function ($) {
  $(document).ready(function () {

    /* URL auto-completion */
    var isDatasetNew = $('body.package.new').length > 0;
    if (true || isDatasetNew) {
      // Set up magic URL slug editor
      CKAN.Dgu.setupUrlEditor('package', false);
      $("#title").focus();
    }


    /* Toggling visibility of time-series/data resources */
    var toggled = function() {
      var isTimeseries = $('input#package_type-timeseries').is(':checked');
      var isIndividual = $('input#package_type-individual').is(':checked');
      if(isTimeseries) {
        $('fieldset#package_type-timeseries').slideDown('fast');
        $('fieldset#package_type-individual').slideUp('fast');
      } else {
        $('fieldset#package_type-timeseries').slideUp('fast');
        $('fieldset#package_type-individual').slideDown('fast');
      }
    };

    $('input#package_type-individual').change(toggled);
    $('input#package_type-timeseries').change(toggled);

    toggled();

    /* Add new rows */
    CKAN.Dgu.copyTableRowOnClick($('#additional_resources-add'), $('#additional_resources-table'));
    CKAN.Dgu.copyTableRowOnClick($('#timeseries_resources-add'), $('#timeseries_resources-table'));
    CKAN.Dgu.copyTableRowOnClick($('#individual_resources-add'), $('#individual_resources-table'));

    /* Hide field sets */
    $('form#package-edit').children('fieldset').hide();
    CKAN.Dgu.showTab($('a#section-name'),                 $('fieldset#section-name-fields'));
    CKAN.Dgu.showTab($('a#section-data'),                 $('fieldset#section-data-fields'));
    CKAN.Dgu.showTab($('a#section-description'),          $('fieldset#section-description-fields'));
    CKAN.Dgu.showTab($('a#section-contacts'),             $('fieldset#section-contacts-fields'));
    CKAN.Dgu.showTab($('a#section-themes'),               $('fieldset#section-themes-fields'));
    CKAN.Dgu.showTab($('a#section-additional_resources'), $('fieldset#section-additional_resources-fields'));
    CKAN.Dgu.showTab($('a#section-temporal'),             $('fieldset#section-temporal-fields'));
    CKAN.Dgu.showTab($('a#section-geographic'),           $('fieldset#section-geographic-fields'));
    $('fieldset#section-name-fields').show();

    /* Setup next/back buttons */
    $('#back-button').attr('disabled', 'disabled');
    $('#back-button').attr('onclick', '').click(function(){
      var activeTab = $('div#form-tabs').find('a.active');
      var previousTab = activeTab.parent().prev().children('a');
      if(previousTab) {
        previousTab.first().trigger('click');
      }
    });

    $('#next-button').attr('onclick', '').click(function(){
      var activeTab = $('div#form-tabs').find('a.active');
      var nextTab = activeTab.parent().next().children('a');
      if(nextTab) {
        nextTab.first().trigger('click');
      }
    });
  });
}(jQuery));

var CKAN = CKAN || {};

CKAN.Dgu = function($, my) {

  my.showTab = function(button, fieldset) {
    button.attr('onclick', '').click(function() {
      $('form#package-edit').children('fieldset').hide();
      $(fieldset).show();
      $('#form-tabs').find('a').removeClass("active");
      $(button).addClass("active");

      // Handle the back/next buttons
      previousTab = $(button).parent().prev();
      if (previousTab.length > 0) {
        $('#back-button').removeAttr('disabled');
      } else {
        $('#back-button').attr('disabled', 'disabled');
      }

      nextTab = $(button).parent().next();
      if (nextTab.length > 0) {
        $('#next-button').removeAttr('disabled');
      } else {
        $('#next-button').attr('disabled', 'disabled');
      }
      
      
    });
  };

  my.copyTableRowOnClick = function(button, table) {
    button.attr('onclick', '').click(function() {
      var lastRow = table.find('tr').last();
      var info = lastRow.attr('class').split('__'); // eg. additional_resources__0
      var prefix = info[0];
      var newIndex = parseInt(info[1],10) + 1;
      var newRow = lastRow.clone();
      newRow.attr('class', prefix + "__" + newIndex);
      newRow.insertAfter(lastRow);
      newRow.find("*").each(function(index, node) {
        var attrValueRegex = new RegExp(prefix + '__\\d+');
        var replacement = prefix + '__' + newIndex;
        
        if ($(node).attr("for")) {
          $(node).attr("for", $(node).attr("for").replace(attrValueRegex, replacement));
        }
        if ($(node).attr("name")) {
          $(node).attr("name", $(node).attr("name").replace(attrValueRegex, replacement));
        }
        $(node).val("");
      });
      newRow.find('a.add-button').remove();
      lastRow.find('a.add-button').appendTo(newRow.find('td').last());
    });
  };

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
