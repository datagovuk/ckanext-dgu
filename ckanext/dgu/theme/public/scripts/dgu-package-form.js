(function ($) {
  $(document).ready(function () {

    var isDatasetNew = preload_dataset === undefined;

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
        fieldset_id = fieldset_id.replace(/-fields$/, '');
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
    CKAN.Dgu.showTab($('a#section-extra'),                $('fieldset#section-extra-fields'));
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

    $('#next-button').removeAttr('disabled');
    $('#next-button').attr('onclick', '').click(function(){
      var activeTab = $('div#form-tabs').find('a.active');
      var nextTab = activeTab.parent().next().children('a');
      if(nextTab) {
        nextTab.removeClass('disabled');
        nextTab.first().trigger('click');
        nextTab.removeClass('disabled');
      }
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
    CKAN.Dgu.setupContactEditDialog($('#contact-dialogbox'));
    CKAN.Dgu.setupContactEditDialog($('#foi-dialogbox'));

    /* Hide/Show the access constraints box when selecting the license_id */
    $('#license_id').change(function(){
      var selectedLicense = $(this).val();
      if(selectedLicense == "uk-ogl"){
        $('#access_constraints').val('');
        $('#access_constraints').hide();
        $('label[for="access_constraints"]').hide();
      } else {
        $('#access_constraints').show();
        $('label[for="access_constraints"]').show();
      }
    });
    $('#license_id').change();

    /* Validate resources buttons */
    $('.validate-resources-button').click(function(){
      $(this).attr({'disabled': 'disabled'});
      var fieldSet = $(this).parent();
      fieldSet.find('span.checking-links-label').show();
      var urlResourceValues = fieldSet.find('input[name$="__url"]').map(function(){return this.value;});
      var urls = [];
      for(var i=0; i<urlResourceValues.length; i++) { urls.push(urlResourceValues[i]); }
      $.ajax({
        url: CKAN.SITE_URL + '/qa/link_checker',
        traditional: true,
        context: fieldSet,
        data: {
          url: urls
        },
        dataType: 'json',
        success: function(data){
          for(var i=0; i<data.length; i++){
            // Populate the format field (if it isn't "htm" or "html")
            var formatField = $(this).find('input[id$="__'+i+'__format"]');
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
                var field = $(this).find('input[id$="__'+i+'__'+requiredFields[j]+'"]');
                showError = field.length >0 && field.val().trim() !== '';
                if(showError){break;}
              }
              if(showError){
                $(this).find('input[id$="__'+i+'__url"]').addClass('field_error').attr({'title': data[i].url_errors[0]});
              } else {
                $(this).find('input[id$="__'+i+'__url"]').removeClass('field_error').removeAttr('title');
              }
            } else {
              $(this).find('input[id$="__'+i+'__url"]').removeClass('field_error').removeAttr('title');
            }
          }
        },
        complete: function(){
          $(this).find('.validate-resources-button').removeAttr('disabled');
          $(this).find('span.checking-links-label').hide();
        }
      });
      
    });

  });
}(jQuery));

var CKAN = CKAN || {};

CKAN.Dgu = function($, my) {

  my.setupContactEditDialog = function(dialogDiv) {
    var fields = ['name', 'email', 'phone'];
    var prefix = dialogDiv.attr('id').split('-')[0]; // e.g. 'contact' or 'foi'

    $('#'+prefix+'-edit').click(function(){dialogDiv.dialog("open");});

    dialogDiv.dialog({
      autoOpen: false,
      height: 300,
      width: 350,
      modal: true,
      buttons: {
        "Save": function() {
          for(var i=0; i<fields.length; i++){
            var fieldName = fields[i];
            var fieldId = '#' + prefix + '-' + fieldName;
            $(fieldId + '-label').text($(fieldId + '-dialog').val());
            $(fieldId).val($(fieldId + '-dialog').val());
          }
          $(this).dialog("close");
        },
        "Cancel": function() {
          for(var i=0; i<fields.length; i++){
            var fieldName = fields[i];
            var fieldId = '#' + prefix + '-' + fieldName;
            $(fieldId + '-dialog').val($(fieldId).val());
          }
          $(this).dialog("close");
        }
      }
    });
  };

  my.showTab = function(button, fieldset) {
    button.attr('onclick', '').click(function() {
      if(button.hasClass('disabled')){ return; }
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
        if ($(node).attr("id")) {
          $(node).attr("id", $(node).attr("id").replace(attrValueRegex, replacement));
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
  }

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


  return my;
}(jQuery, CKAN.Dgu || {});
