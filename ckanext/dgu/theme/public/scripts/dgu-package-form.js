
(function ($) {
  $(document).ready(function () {

    var isDatasetNew = $('body.PackageController.new').length > 0;

    for (field_id in form_errors) {
      
      var errors = form_errors[field_id];
      if( ! errors.length) { return; }

      // errors could be nested, in which case it's a list of objects.
      // We need to find the first reference to an error in the list of
      // objects, and pull out a field_id from that.
      if( typeof(errors[0]) === "object" ){
        found = false;
        for(var i=0; i<errors.length && !found; i++){
          for(key in errors[i]){
            field_id = field_id + '__' + i + '__' + key;
            found = true;
            break;
          }
        }
      }
      var field = $('#'+field_id);
      if (field !== undefined && field.length > 0) {
        var fieldset_id = field.parents('fieldset').last().attr('id');
        fieldset_id = fieldset_id.replace(/-fields?$/, '');
        $('#'+fieldset_id).addClass('fieldset_button_error');
      }
    }

    /* URL auto-completion */
    if (isDatasetNew) {
      // Set up magic URL slug editor
      CKAN.Dgu.setupUrlEditor('package', false);
      $("#title").focus();
    }


    /* Toggling visibility of time-series/data resources */
    var toggled = function() {
      var isTimeseries = $('input#package_type-timeseries-radio').is(':checked');
      var isIndividual = $('input#package_type-individual-radio').is(':checked');
      var fieldsetTimeseries = $('fieldset#package_type-timeseries');
      var fieldsetIndividual = $('fieldset#package_type-individual');
      if(isTimeseries) {
        fieldsetTimeseries.show();
        fieldsetIndividual.hide();
      } else {
        fieldsetTimeseries.hide();
        fieldsetIndividual.show();
      }
    };

    $('input#package_type-individual-radio, input#package_type-timeseries-radio').change(toggled);
    toggled();

    /* Handle prev/next buttons */
    $('.package_create_form #form-tabs a').on('shown', CKAN.Dgu.updatePublisherNav);

    /* Add new rows */
    CKAN.Dgu.copyTableRowOnClick($('#additional_resources-add'), $('#additional_resources-table'));
    CKAN.Dgu.copyTableRowOnClick($('#timeseries_resources-add'), $('#timeseries_resources-table'));
    CKAN.Dgu.copyTableRowOnClick($('#individual_resources-add'), $('#individual_resources-table'));

    /* Hide field sets */
    $('form#package-edit').children('fieldset').hide();
    $('fieldset#section-name-fields').show();

    /* Setup next/back buttons */
    var clickNav = function(goBack) {
      return function(e) {
        e.preventDefault();
        var activeTab = $('div#form-tabs li.active');
        if (goBack) { 
          activeTab.prev().children('a').click(); 
        }
        else {
          activeTab.next().children('a').click(); 
          activeTab.next().removeClass('disabled');
        }
      };
    };

    // Correctly handle disabled nav buttons
    $('a.disabled').click(function(e) { 
      e.preventDefault();
    });

    $('#back-button').click(function(e) {
        e.preventDefault();
        var activeTab = $('div#form-tabs li.active');
        activeTab.prev().children('a').click(); 
    });
    $('#next-button').click(function(e) {
        e.preventDefault();
        var nextLink = $('div#form-tabs li.active').next().children('a');
        if (nextLink.hasClass('disabled')) {
          // Hook up the link with bootstrap
          nextLink.attr('data-toggle', 'tab');
          // Allow it to be clicked
          nextLink.removeClass('disabled');
        }
        // Click it
        nextLink.click();
    });

    /* Tag auto-completion */
    CKAN.Dgu.setupTagAutocomplete($('input.autocomplete-tag'));

    /* Auto-fill contact and FOI information based upon selected publisher */
    var publisherInfoFields = [
      "contact-name",
      "contact-email",
      "contact-phone",
      "foi-name",
      "foi-email",
      "foi-phone"
    ];
    $('#groups__0__name').change(function() {
      var selectedPublisherName = $(this).val();
      var publisher = publishers[selectedPublisherName];
      if(publisher === undefined){
        publisher = {};
        for(var i=0; i<publisherInfoFields.length; i++){
          publisher[publisherInfoFields[i]] = '';
        }
      }
      for(var i=0; i<publisherInfoFields.length; i++){
        $('#' + publisherInfoFields[i]).val(publisher[publisherInfoFields[i]]);
        $('#' + publisherInfoFields[i] + '-dialog').val(publisher[publisherInfoFields[i]]);
        $('#' + publisherInfoFields[i] + '-label').text(publisher[publisherInfoFields[i]]);
      }
    });

    /* Create dialog boxes for editing the contact and foi information */
    CKAN.Dgu.setupEditorDialogs();

    /* Hide/Show the access constraints box when selecting the license_id */
    $('#license_id').change(function(){
      var selectedLicense = $(this).val();
      if(selectedLicense == "uk-ogl"){
        $('#access_constraints').val('');
        $('.choose-other-licence').hide();
      } else {
        $('.choose-other-licence').show();
      }
    });
    $('#license_id').change();

    /* Can't switch between timeseries/individual if you've got any resources */
    CKAN.Dgu.setupResourcesToggle();

    /* Validate resource buttons */
    $('.validate-resources-button').each(function(index, e){ // validate all resources
      CKAN.Dgu.validateResource(e, function(){return $(e).parent().find('tr.resource');});
    });
    $('.validate-resource-button').each(function(index, e){ // validate individual resource
      CKAN.Dgu.validateResource(e, function(){return $(e).parents('tr.resource');});
    });

  });
}(jQuery));

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

  my.setupUrlEditor = function(slugType,readOnly) {
    // Page elements to hook onto
    var titleInput = $('.js-title');
    var urlText = $('.js-url-text');
    var urlSuffix = $('.js-url-suffix');
    var urlInput = $('.js-url-input');
    var validMsg = $('.js-url-is-valid');

    if (titleInput.length==0) return;
    if (urlText.length==0) return;
    if (urlSuffix.length==0) return;
    if (urlInput.length==0) return;
    if (validMsg.length==0) return;

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
            if(formatField.val().trim() == "" && !data[i].inner_format.match(/^html?$/) ){
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
