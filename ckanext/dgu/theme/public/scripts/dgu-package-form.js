
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
      var urlEditor = new CKAN.Dgu.UrlEditor({ 'slugType': 'package'});
      $("#title").focus();
    }

    /* Handle prev/next buttons */
    $('.package_create_form #form-tabs a').on('shown', CKAN.Dgu.updatePublisherNav);

    /* Show the correct resource fieldset */
    CKAN.Dgu.showHideResourceFieldsets();
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

  });
}(jQuery));

