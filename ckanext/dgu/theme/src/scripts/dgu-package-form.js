  $(function() {
    assert(window.form_errors, 'window.form_errors not set');

    var isDatasetNew = $('body.PackageController.new').length > 0;
    var errorFieldsets = [];

    for (field_id in window.form_errors) {

      var errors = window.form_errors[field_id];
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
        errorFieldsets.push(fieldset_id);
        fieldset_id = fieldset_id.replace(/-fields?$/, '');
        $('#'+fieldset_id).addClass('fieldset_button_error');
      }
    }

    if (errorFieldsets.length>0) {
      window.location.hash = 'tab-'+errorFieldsets[0];
    }

    /* URL auto-completion */
    if (isDatasetNew) {
      // Set up magic URL slug editor
      var urlEditor = new CKAN.Dgu.UrlEditor({ 'slugType': 'package'});
      $("#title").focus();
    }

    /* Handle prev/next buttons */
    $('.package_create_form a[data-toggle="tab"]').on('click', function(e) {
      var target = $(e.delegateTarget);
      if (target.hasClass('disabled')) {
        e.preventDefault();
        return false;
      }
    });
    $('.package_create_form a[data-toggle="tab"]').on('click', function(e) {
      var target_a = $(e.target);
      var target_li = target_a.parent();
      var hasPrevious = target_li.prev().length > 0;
      var hasNext = target_li.next().length > 0;

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
    });

    /* Show the correct resource fieldset */
    CKAN.Dgu.showHideResourceFieldsets();
    /* Add new rows */
    CKAN.Dgu.copyTableRowOnClick($('#additional_resources-add'), $('#additional_resources-table'));
    CKAN.Dgu.copyTableRowOnClick($('#timeseries_resources-add'), $('#timeseries_resources-table'));
    CKAN.Dgu.copyTableRowOnClick($('#individual_resources-add'), $('#individual_resources-table'));


    function add_extra_select(list_selector) {
      return function(e){
        console.log('add_extra_select 3');
        var list = $(list_selector);

        var new_select = list.find('select').first().clone();

        new_select.removeAttr('value');
        new_select.removeAttr('style');
        new_select.removeAttr('id');
        new_select.removeClass('chzn-done');

        var new_list_item = $('<li></li>').append(new_select);

        list.append(new_list_item);

        new_select.chosen({allow_single_deselect: true});

        return false;
      }
    }
    $('#schema-add').click(add_extra_select('#schema-list'));
    $('#codelist-add').click(add_extra_select('#codelist-list'));

    $('#mandates-add').click(function(e) {
        var list = $('#mandate-list');

        var new_mandate = list.children().first().clone();

        new_mandate.children().first().attr('value', '');

        list.append(new_mandate);
      
        return false;
    });

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
          nextLink.removeAttr('disabled');
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
      "foi-web",
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
      if(selectedLicense == "" || selectedLicense == "__extra__"){
        $('.choose-other-licence').show();
      } else {
        $('#access_constraints').val('');
        $('.choose-other-licence').hide();
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

    /* Up/down buttons */
    $('.resource-move').each(function(index, button){ // validate individual resource
      button = $(button);
      CKAN.Dgu.bindResourceMoveButtons(button, function(){return button.parents('tr.resource');});
    });
    /* Up/down button visibility */
    var flexitables = $('.resource-move').parents('table');
    $.each( flexitables, function(i,table) {
      CKAN.Dgu.setVisibleResourceMoveButtons($(table));
    });

    /* Resource format autocomplete */
    $('.format-typeahead').autocomplete({source: DGU_RESOURCE_FORMATS, items:5});

    /* Additional resources scraper fields */
    CKAN.Dgu.setupAdditionalResourcesScrapers();

    /* Apply a datepicker to all date rows */
    $('.needs-datepicker').datepicker({dateFormat:'dd/mm/yy'});
  });

  function update_themes() {
      $('#check-themes').attr('disabled', 'disabled');

      var name = $('#name').val();
      var title = $('#title').val();
      var notes = $('#notes').val();
      var tags = $('#tag_string').val();

      $.ajax({
        url: "/api/3/action/suggest_themes",
        data: encodeURIComponent(JSON.stringify({name: name,
                                                 title: title,
                                                 notes: notes,
                                                 tags: tags})),
        type: "POST",
        dataType: "json",
        success: function(obj) {
            var nm = obj.result['primary-theme'].name;
            $('#theme-primary-label').html(nm || "None");
            $('#theme-primary').val(nm || "");
 
            $('#theme-primary-reasons').empty();
            var reasons = obj.result['primary-theme'].reasons || [];

            if (reasons.length > 0) {
              $('#theme-primary-reasons-label').show()
            } else {
              $('#theme-primary-reasons-label').hide()
            }

            for (i = 0; i < reasons.length; i++) {
               $('#theme-primary-reasons').append('<li>' + reasons[i] + '</li>');
            }

            nm = '';

            var secondaries = obj.result['secondary-theme'];
            var all_reasons = [];
            for (var i = 0; i < secondaries.length; i++) {
                var th = secondaries[i].name;
                nm = nm + th;
                if ( i != secondaries.length-1 ) {
                  nm = nm + ", "
                }
                reasons = secondaries[i].reasons || []
                for (j = 0; j < reasons.length; j++) {
                  all_reasons.push(th + ' - ' + reasons[j]);
                }
            }

            $('#theme-secondary').val(nm);
            if (nm === '') {
              nm = 'None'
            }
            $('#theme-secondary-label').html(nm);

            if (all_reasons.length > 0) {
              $('#theme-secondary-reasons-label').show()
            } else {
              $('#theme-secondary-reasons-label').hide()
            }

            $('#theme-secondary-reasons').empty();
            for (i = 0; i < all_reasons.length; i++) {
               $('#theme-secondary-reasons').append('<li>' + all_reasons[i] + '</li>');
            }

            $('#check-themes').removeAttr('disabled');
        }
      });
  }

  $(function() {
    $('#notes').focusout(update_themes);
    $('#reveal-tags').click(function(){
      $('#tags').show(400, function() {
        $('html, body').animate({
          scrollTop: $("#tags").offset().top
        }, 400);
      });
      return false;
    });
  });
