jQuery(function ($) {

  $(document).ready(function () {
    /* Create javascript tooltips */
    $('.js-tooltip').tooltip();
    $('.js-tooltip-instruction-needed').attr('title', 'Tooltip text required?');
    $('.js-tooltip-instruction-needed').tooltip({'extraClass':'instruction-needed'});

    $('.instruction-needed').tooltip({'extraClass':'instruction-needed'});

    $('.to-be-completed').addClass('js-tooltip-to-be-completed');
    $('.js-tooltip-to-be-completed').tooltip({'extraClass':'to-be-completed'});

    /* Star ratings have gorgeous HTML tooltips */
    $('.star-rating').each(function(i,el) {
      el = $(el);
      el.tooltip({ 
        title: el.find('.tooltip').html(), 
        placement: 'right' 
      });
    });

    /* Toggle visibility of sub-publishers on the publisher/read.html page */
    $('#sub-publisher-toggle').click(function(){
      $('#sub-publishers li.collapsed').toggle();
    });

    /* Reveal in search results facets */
    $('.js-more-button').click(function(e){
      e.preventDefault();
      var id = $(e.target).attr('id');
      console.log( id );
      $(e.target).remove();
      $('#'+id+'-items').toggle();
    });  

    $('input[name="dataset-results-sort"]').change(function(e){
      e.preventDefault();
      window.location = $(this).val()
    });
    $('input[name="publisher-results-include-subpub"]').change(function(e){
      e.preventDefault();
      window.location = $(this).val()
    });

    // Buttons with href-action should navigate when clicked
    $('input.href-action').click(function(e) {
      e.preventDefault();
      window.location = ($(e.target).attr('action'));
    });
  });

});

var CKAN = CKAN || {};

CKAN.Dgu = function($, my) {

  my.setupEditorDialogs = function() {
    // Bind to the 'save' button, which writes values back to the document
    $('.dgu-editor-save').click(function(e) {
      var inputs = $(e.target).parents('.dgu-editor').find('input');
      $.each(inputs, function(i, input) {
        input = $(input);
        var targetLabel = input.attr('data-label');
        var targetInput = input.attr('data-input');
        // Update the text label in the page
        if (targetLabel)  {  $(targetLabel).text(input.val()); }
        // Update the hidden input which stores the true value
        if (targetInput)  {  $(targetInput).val(input.val());  }
      });
    });

    $('.dgu-editor').on('shown', function(e) {

      // Populate the inputs with the values of their targets.
      var modal = $(e.target);
      var inputs = modal.find('input');
      $.each(inputs, function(i, input) {
        input = $(input);
        var targetInput = input.attr('data-input');
        if (targetInput)  { 
          input.val($(targetInput).val()); 
        }
      });

      // Be nice. Focus the first input when the dialog appears.
      var firstInput = $(e.target).find('input')[0];
      $(firstInput).focus();
    });

    $('.dgu-editor input[type="text"]').bind('keydown', function(e) {
      // Capture the Enter key
      if (e.keyCode==13) {
        // DO NOT SUBMIT THE FORM! (Really annoying!)
        e.preventDefault();
        // Instead, confirm the dialog box
        $(e.target).parents('.dgu-editor').find('.dgu-editor-save').click();
      }
    });
  };

  my.setupResourcesToggle = function() {
    var elements = $('#package_type-timeseries input[type="text"], #package_type-individual input[type="text"]');
    /* If any inputs contain text, then disable the radio toggles */
    var updateToggle = function(e) {
      var allEmpty = true;
      $.each(elements, function(i, el) {
        var v = el.value;
        if (v.length) {
          allEmpty = false;
        }
      });
      if (allEmpty) {
        $('#package_type-individual-radio').removeAttr('disabled');
        $('#package_type-timeseries-radio').removeAttr('disabled');
        $('.record-type-disabled').hide();
      }
      else {
        $('#package_type-individual-radio').attr({'disabled':'disabled'});
        $('#package_type-timeseries-radio').attr({'disabled':'disabled'});
        $('.record-type-disabled').show();
      }
    };
    elements.change(updateToggle);
    updateToggle();
  };

  my.copyTableRowOnClick = function(button, table) {
    button.attr('onclick', '').click(function() {
      var lastRow = table.find('tr').last();
      var info = lastRow.attr('class').split('__'); // eg. additional_resources__0
      var prefix = info[0];
      var newIndex = parseInt(info[1],10) + 1;
      var newRow = lastRow.clone();
      newRow.attr('class', prefix + "__" + newIndex);
      newRow.addClass("resource");
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
        if ($(node).attr("id")) {
          $(node).attr("id", $(node).attr("id").replace(attrValueRegex, replacement));
        }
        $(node).val("");
        $(node).removeClass("field_error");
      });
      newRow.find('a.add-button').remove();
      lastRow.find('a.add-button').appendTo(newRow.find('td').last());

      // Check URL button
      newRow.find('input[id$="__validate-resource-button"]').attr('value', 'Check')
                                                            .removeAttr('disabled')
                                                            .each(function(index, e){
        CKAN.Dgu.validateResource(e, function(){return $(e).parents('tr.resource');});
      });
    });
  };

  my.bindInputChanges = function(input, callback) {
    input.keyup(callback);
    input.keydown(callback);
    input.keypress(callback);
    input.change(callback);
  };

  my.updatePublisherNav = function(e) {
    var hasPrevious = $(e.target).parent().prev().length > 0;
    var hasNext = $(e.target).parent().next().length > 0;

    // Handle the back/next buttons
    if (hasPrevious) {
      $('#back-button').removeAttr('disabled');
    } else {
      $('#back-button').attr('disabled', 'disabled');
    }

    if (hasNext) {
      $('#next-button').removeAttr('disabled');
    } else {
      $('#next-button').attr('disabled', 'disabled');
    }
  };

  my.setupTagAutocomplete = function(elements) {
    elements
      // don't navigate away from the field on tab when selecting an item
      .bind( "keydown", function( event ) {
        if ( event.keyCode === $.ui.keyCode.TAB &&
            $( this ).data( "autocomplete" ).menu.active ) {
          event.preventDefault();
        }
      })
      .autocomplete({
        minLength: 1,
        source: function(request, callback) {
          // here request.term is whole list of tags so need to get last
          var _realTerm = request.term.split(',').pop().trim();
          var url = CKAN.SITE_URL + '/api/2/util/tag/autocomplete?incomplete=' + _realTerm;
          $.getJSON(url, function(data) {
            // data = { ResultSet: { Result: [ {Name: tag} ] } } (Why oh why?)
            var tags = $.map(data.ResultSet.Result, function(value, idx) {
              return value.Name;
            });
            callback(
              $.ui.autocomplete.filter(tags, _realTerm)
            );
          });
        },
        focus: function() {
          // prevent value inserted on focus
          return false;
        },
        select: function( event, ui ) {
          var terms = this.value.split(',');
          // remove the current input
          terms.pop();
          // add the selected item
          terms.push( " "+ui.item.value );
          // add placeholder to get the comma-and-space at the end
          terms.push( " " );
          this.value = terms.join( "," );
          return false;
        }
    });
  };

  /**
   * Setup the given button to validate the given resource URLs.
   *
   * button - the button that when pressed triggers the validation
   * getResources - a callable that returns the <tr> resources to validate
   **/
  my.validateResource = function(button, getResources) {
    $(button).click(function(){
      $(this).attr({'disabled': 'disabled'});
      $(this).siblings('span.checking-links-label').show();
      var resources = getResources();
      var urlResourceValues = $(resources).map(function(){
        return $(this).find('input[name$="__url"]').val();
      });
      var urls = []; // copy url values in order that data serialises correctly in
                     // the ajax request.  I don't know why it doesn't work otherwise.
      for(var i=0; i<urlResourceValues.length; i++) { urls.push(urlResourceValues[i]); }

      $.ajax({
        url: CKAN.SITE_URL + '/qa/link_checker',
        traditional: true,
        context: resources,
        data: { url: urls },
        dataType: 'json',
        success: function(data){
          for(var i=0; i<data.length; i++){
            // Populate the format field (if it isn't "htm" or "html")
            var formatField = $(this[i]).find('input[id$="__format"]');
            var fmt = data[i].inner_format
            if(formatField.val().trim() == "" && !fmt.match(/^html?$/) ){
              formatField.val(data[i].inner_format);
            }

            // Indicate any url errors
            if(data[i].url_errors.length) {
              // If an empty url field, then only display error if there's at least one
              // other non-empty field in that row.
              var requiredFields = ["url", "description", "format", "date"];
              var showError = false;
              for(var j=0; j<requiredFields.length; j++){
                var field = $(this[i]).find('input[id$="__'+requiredFields[j]+'"]');
                showError = field.length >0 && field.val().trim() !== '';
                if(showError){break;}
              }
              if(showError){
                $(this[i]).find('input[id$="__url"]').addClass('field_error').attr({'title': data[i].url_errors[0]});
              } else {
                $(this[i]).find('input[id$="__url"]').removeClass('field_error').removeAttr('title');
              }
            } else {
              $(this[i]).find('input[id$="__url"]').removeClass('field_error').removeAttr('title');
            }
          }
        },
        complete: function(){
          $(button).removeAttr('disabled');
          $(button).siblings('span.checking-links-label').hide();
        },
        timeout: 10000
      });
    });
  };

  return my;
}(jQuery, CKAN.Dgu || {});


CKAN.Dgu.UrlEditor = Backbone.View.extend({
  initialize: function() {
    _.bindAll(this,'titleToSlug','titleChanged','urlChanged','checkSlugIsValid','apiCallback');

    // Initial state
    var self = this;
    this.updateTimer = null;
    this.titleInput = $('.js-title');
    this.urlInput = $('.js-url-input');
    this.validMsg = $('.js-url-is-valid');
    this.lengthMsg = $('.url-is-long');
    this.lastTitle = "";
    this.disableTitleChanged = false;

    // Settings
    this.regexToHyphen = [ new RegExp('[ .:/_]', 'g'),
                      new RegExp('[^a-zA-Z0-9-_]', 'g'),
                      new RegExp('-+', 'g')];
    this.regexToDelete = [ new RegExp('^-*', 'g'),
                      new RegExp('-*$', 'g')];

    // Default options
    if (!this.options.apiUrl) {
      this.options.apiUrl = CKAN.SITE_URL + '/api/2/util/is_slug_valid';
    }
    if (!this.options.MAX_SLUG_LENGTH) {
      this.options.MAX_SLUG_LENGTH = 90;
    }
    this.originalUrl = this.urlInput.val();

    // Hook title changes to the input box
    CKAN.Dgu.bindInputChanges(this.titleInput, this.titleChanged);
    CKAN.Dgu.bindInputChanges(this.urlInput, this.urlChanged);

    // If you've bothered typing a URL, I won't overwrite you
    function disable() {
      self.disableTitleChanged = true;
    };
    this.urlInput.keyup   (disable);
    this.urlInput.keydown (disable);
    this.urlInput.keypress(disable);

    // Set up the form
    this.urlChanged();
  },

  titleToSlug: function(title) {
    var slug = title;
    $.each(this.regexToHyphen, function(idx,regex) { slug = slug.replace(regex, '-'); });
    $.each(this.regexToDelete, function(idx,regex) { slug = slug.replace(regex, ''); });
    slug = slug.toLowerCase();

    if (slug.length<this.options.MAX_SLUG_LENGTH) {
        slug=slug.substring(0,this.options.MAX_SLUG_LENGTH);
    }
    return slug;
  },

  /* Called when the title changes */
  titleChanged:  function() {
    if (this.disableTitleChanged) { return; }
    var title = this.titleInput.val();
    if (title == this.lastTitle) { return; }
    this.lastTitle = title;

    slug = this.titleToSlug(title);
    this.urlInput.val(slug);
    this.urlInput.change();
  },

  /* Called when the url is changed */
  urlChanged: function() {
    var slug = this.urlInput.val();
    if (this.updateTimer) { clearTimeout(this.updateTimer); }
    if (slug.length<2) {
      this.validMsg.html('<span style="font-weight: bold; color: #444;">URL is too short.</span>');
    }
    else if (slug==this.originalUrl) {
      this.validMsg.html('<span style="font-weight: bold; color: #000;">This is the current URL.</span>');
    }
    else {
      this.validMsg.html('<span style="color: #777;">Checking...</span>');
      var self = this;
      this.updateTimer = setTimeout(function () {
        self.checkSlugIsValid(slug);
      }, 200);
    }
    if (slug.length>20) {
      this.lengthMsg.show();
    }
    else {
      this.lengthMsg.hide();
    }
  },

  checkSlugIsValid: function(slug) {
    $.ajax({
      url: this.options.apiUrl,
      data: 'type='+this.options.slugType+'&slug=' + slug,
      dataType: 'jsonp',
      type: 'get',
      jsonpCallback: 'callback',
      success: this.apiCallback
    });
  },

  /* Called when the slug-validator gets back to us */
  apiCallback: function(data) {
    if (data.valid) {
      this.validMsg.html('<span style="font-weight: bold; color: #0c0">This URL is available!</span>');
    } else {
      this.validMsg.html('<span style="font-weight: bold; color: #c00">This URL is not available.</span>');
    }
  }
});
