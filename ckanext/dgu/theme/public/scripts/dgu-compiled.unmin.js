/*! DGU+CKAN Application JS concatenated 2013-07-17 */

/* Utility: Global assertion function */
function assert( code, errorMessage ) {
  if (!code) {
    console.error(errorMessage, arguments);
    throw ('AssertionError');
  }
}

/* Utility: Global console.log() function for all browsers */
(function (con) {
  var method;
  var dummy = function() {};
  var methods = ('assert,count,debug,dir,dirxml,error,exception,group,' +
     'groupCollapsed,groupEnd,info,log,markTimeline,profile,profileEnd,' +
     'time,timeEnd,trace,warn').split(',');
  while (method = methods.pop()) {
    con[method] = con[method] || dummy;
  }
})(window.console = window.console || {});


/* Core JS */
jQuery(function () {

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
        placement: 'right',
        template: '<div class="tooltip star-rating-tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>',
        delay: 0,
        animation: false

      });
    });

    /* Reveal in search results facets */
    $('.facet-expand-collapse').click(function(e){
      e.preventDefault();
      var target = $(e.delegateTarget); // Using e.target might accidently catch the <img>
      var id = target.attr('id');
      target.toggleClass('expanded');
      $('#'+id+'-items').toggle('fast');
    });

    $('select[name="dataset-results-sort"]').change(function(e){
      e.preventDefault();
      window.location = $(this).val() + '#search-sort-by';
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
    function clickToggle(e) {
      var to = e.target.value;
      if (to=='individual') {
        $('#package_type_modal').modal('toggle');
      }
      else {
        doToggle(to);
      }
    }
    function cancelChange(e) {
      e.preventDefault();
      var active = $('input:radio[name=package_type]:not(:checked)').click();
    }
    function doToggle(mode) {
      var alt;
      if (mode=='individual') alt='timeseries';
      else if (mode=='timeseries') alt='individual';
      else throw 'Cannot toggle to mode='+mode;
      var from = $('#'+ alt+'_resources-table');
      var to =   $('#'+mode+'_resources-table');
      // Copy the data
      CKAN.Dgu.copyResourceTable(from,to);
      // Wipe the old table
      var newRow = CKAN.Dgu.addTableRow(from);
      from.find('tbody tr').not(newRow).remove();
      CKAN.Dgu.showHideResourceFieldsets();
    }
    $('#package_type_modal .cancel').click(cancelChange);
    $('#package_type_modal .ok').click(function(){doToggle('individual')});
    $('input:radio[name=package_type]').change(clickToggle);
  };

  /* Toggling visibility of time-series/data resources */
  my.showHideResourceFieldsets = function() {
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

  my.copyResourceTable = function(_from, _to) {
    var from = _from.find('tbody tr');
    var to = _to.find('tbody tr');
    while (to.length < from.length) {
      to.push(CKAN.Dgu.addTableRow(_to));
    }
    if (to.length!=from.length) throw "DOM insanely broken.";
    for (var i=0;i<to.length;i++) {
      // Map out the target elements; { 'url':<HTMLInput> .. }
      var inputMap = {};
      $.each( $(to[i]).find('input'), function(ii, input) {
        input = $(input);
        var name = input.prop('name').split('__')[2];
        inputMap[name] = input;
      });
      // Copy from the source elements
      $.each( $(from[i]).find('input'), function(ii, input) {
        input = $(input);
        var name = input.prop('name').split('__')[2];
        if (name in inputMap) {
          inputMap[name].val( input.val() )
        }
      });
    }
  };

  my.addTableRow = function(table) {
      var lastRow = table.find('tbody tr:last');
      var oldClass = lastRow.prop('class');
      var info = oldClass.split('__'); // eg. additional_resources__0
      var prefix = info[0];
      var newIndex = parseInt(info[1],10) + 1;
      var newRow = lastRow.clone();
      newRow.removeClass(oldClass);
      newRow.addClass( prefix + "__" + newIndex);
      newRow.addClass('resource');
      newRow.insertAfter(lastRow);
      newRow.find("*").each(function(index, node) {
        var attrValueRegex = new RegExp(prefix + '__\\d+');
        var replacement = prefix + '__' + newIndex;

        if ($(node).prop("for")) {
          $(node).prop("for", $(node).prop("for").replace(attrValueRegex, replacement));
        }
        if ($(node).prop("name")) {
          $(node).prop("name", $(node).prop("name").replace(attrValueRegex, replacement));
        }
        if ($(node).prop("id")) {
          $(node).prop("id", $(node).prop("id").replace(attrValueRegex, replacement));
        }
        $(node).val("");
        $(node).removeClass("error");
      });
      newRow.find('a.add-button').remove();
      lastRow.find('a.add-button').appendTo(newRow.find('td').last());

      // Check URL button
      var validateButton = newRow.find('button[id$="__validate-resource-button"]');
      if (validateButton.length==0) { throw 'Bad CSS selector. Could not attach event handler.'; }
      validateButton.attr('value', 'Check')
                     .removeAttr('disabled')
                     .each(function(index, e){
        CKAN.Dgu.validateResource(e, function(){return $($(e).parents('tr')[0]);});
      });
      // Up/Down buttons
      $.each( newRow.find('.resource-move'), function(i, button) {
        CKAN.Dgu.bindResourceMoveButtons($(button));
      });
      // Reset button visiblity
      CKAN.Dgu.setVisibleResourceMoveButtons(table);
      return newRow;
  };

  my.copyTableRowOnClick = function(button, table) {
    button.attr('onclick', '').click(function() {
      CKAN.Dgu.addTableRow(table);
    });
  };

  my.bindInputChanges = function(input, callback) {
    input.keyup(callback);
    input.keydown(callback);
    input.keypress(callback);
    input.change(callback);
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
          var _realTerm = $.trim( request.term.split(',').pop() );
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

  my.bindResourceMoveButtons = function(button) {
    button.bind('click',function(e){
      e.preventDefault();
      var target = $(e.delegateTarget);
      var table = target.closest('table');
      var rows = table.find('tr');
      var index = table.find('tr').index(target.closest('tr'));
      // Should be going either up or down
      var up   = target.hasClass('resource-move-up');
      var down = target.hasClass('resource-move-down');
      assert( (up&&!down) || (!up&&down), 'up XOR down should be true: '+up+','+down);
      // Function to exchange the <INPUT> values between two rows
      // Trust me, this is simpler than trying to manipulate the table
      function swapValues( tr1, tr2 ) {
        assert(tr1.length);
        var input1 = tr1.find('input[type="text"]');
        var input2 = tr2.find('input[type="text"]');
        assert( input1.length>0, 'Found no inputs to swap', tr1 );
        for (var i=0;i<input1.length;i++) {
          var a = $(input1[i]);
          var b = $(input2[i]);
          var swap = a.val();
          a.val( b.val() );
          b.val( swap );
        }

        // Copy all elements inside tr1.hidden-resource-fields to tr1.hidden_resource-fields
        // we know there is at least one hidden field, the id and we should get them so we know
        // what we are swapping
        var hidden1 = tr1.find('.hidden-resource-fields')
        console.log(hidden1)
        var id1 = hidden1.find('input[type="hidden"]').get(0)
        console.log(id1)
        id1 = $(id1).attr('name').match(/__\d+__/gi)[0]
        console.log(id1)

        var hidden2 = tr2.find('.hidden-resource-fields')
        console.log(hidden1)
        var id2 = hidden2.find('input[type="hidden"]').get(0)
        console.log(id2)
        id2 = $(id2).attr('name').match(/__\d+__/gi)[0]
                console.log(id2)

        // Swap the HTML over from one TD to the other.
        var swap = hidden2.html()
        hidden2.html(hidden1.html())
        hidden1.html(swap)

        var firstReplacer = new RegExp(id2, 'g')
        var secondReplacer = new RegExp(id1, 'g')

        hidden1.find('input[type="hidden"]').each(function(){
            // Replace the old ID we copied across with the new ID for this container
            var new_id = $(this).attr('name').replace(firstReplacer, id1)
            $(this).attr('id', new_id)
            $(this).attr('name', new_id)
        })

        hidden2.find('input[type="hidden"]').each(function(){
            // Replace the old ID we copied across with the new ID for this container
            var new_id = $(this).attr('name').replace(secondReplacer, id2)
            $(this).attr('id', new_id)
            $(this).attr('name', new_id)
        })
      }

      if (up) {
        assert(index>1, 'First up button should be disabled');
        assert(index<rows.length-1, 'Last up button should be disabled');
        // Array splice upwards
        swapValues( $(rows[index]), $(rows[index-1]) );
      }
      if (down) {
        assert(index<rows.length-2, 'Last down button should be disabled');
        // Array splice downwards
        swapValues( $(rows[index]), $(rows[index+1]) );
      }
      CKAN.Dgu.setVisibleResourceMoveButtons(table);
      return false;
    });
  };

  my.setVisibleResourceMoveButtons = function(table) {
    /* Update the visibility of resource-move buttons.
     * In simple terms: The final two buttons are invisible.
     * Of the visible ones, the first "Up" and last "Down" buttons are disabled.  */
    var all = table.find('.resource-move');
    $.each( all, function(i, element) {
      element = $(element);
      disabled = (i==0 || i>=all.length-3);
      element.attr('disabled',disabled);
      visible = (i>=all.length-2) ? 'none':'inline-block';
      element.css('display',visible);
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
            var fmt = data[i].format

            if($.trim(formatField.val()) == "" && !fmt.match(/^html?$/) ){
              formatField.val(data[i].format);
            }

            // Indicate any url errors
            if(data[i].url_errors.length) {
              // If an empty url field, then only display error if there's at least one
              // other non-empty field in that row.
              var requiredFields = ["url", "description", "format", "date"];
              var showError = false;
              for(var j=0; j<requiredFields.length; j++){
                var field = $(this[i]).find('input[id$="__'+requiredFields[j]+'"]');
                showError = field.length >0 && $.trim(field.val()) !== '';
                if(showError){break;}
              }
              if(showError){
                $(this[i]).find('input[id$="__url"]').parent().addClass('error').attr({'title': data[i].url_errors[0]});
              } else {
                $(this[i]).find('input[id$="__url"]').parent().removeClass('error').removeAttr('title');
              }
            } else {
              $(this[i]).find('input[id$="__url"]').parent().removeClass('error').removeAttr('title');
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

  my.setupAdditionalResourcesScrapers = function() {
    var updateScraperField = function( formatField ) {
      formatField = $(formatField);
      var tr = formatField.closest('tr');
      var scraperField = tr.find('.input_additional_resources_scraper');
      assert(scraperField.length==1);
      if ( $.trim( formatField.val().toUpperCase() )=='HTML' ) {
        scraperField.removeAttr('disabled');
        scraperField.css('text-decoration', 'none');
      }
      else {
        scraperField.attr('disabled','disabled');
        scraperField.css('text-decoration', 'line-through');
      }
    };
    var inputFormat = $('.input_additional_resources_format');
    /* Set initial state */
    inputFormat.each( function(i,x) {updateScraperField(x); } );
    /* Bind to state changes */
    var onChange = function(e) { updateScraperField( e.delegateTarget ); };
    inputFormat.bind('keyup', onChange);
    inputFormat.bind('keypress', onChange);
    inputFormat.bind('change', onChange);
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
    }
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


$(function() {
  var spinConfig = {
    lines: 9, // The number of lines to draw
    length: 3, // The length of each line
    width: 2, // The line thickness
    radius: 4, // The radius of the inner circle
    rotate: 3, // The rotation offset
    color: '#FFF', // #rgb or #rrggbb
    speed: 2.1, // Rounds per second
    trail: 43, // Afterglow percentage
    shadow: true, // Whether to render a shadow
    hwaccel: false, // Whether to use hardware acceleration
    className: 'spinner', // The CSS class to assign to the spinner
    zIndex: 2e9, // The z-index (defaults to 2000000000)
    top: 'auto', // Top position relative to parent in px
    left: 'auto' // Left position relative to parent in px
  };

  var basketUiContainer = $('#shopping-basket-container');
  if (basketUiContainer.length==0) {
    // No basket exists on this page
    return;
  }

  var basketUi = $('#shopping-basket');
  var basketResetButton = $('#shopping-basket-reset');
  var basketSubmitButton = $('#shopping-basket-submit');
  var basketCache = [];
  var spinners = [];

  var disable = function() {
    // Disable the UI
    $.each($('.btn-basket'), function(i, el) {
      spinners.push(new Spinner(spinConfig).spin(el));
      $(el).find('span').css('opacity', '0.1');
      $(el).attr({'disabled': 'disabled'});
    });
    basketUi.empty();
    spinners.push(new Spinner(spinConfig).spin(basketUi[0]));
  };

  var renderBasket = function(basket) {
    // Enable the UI
    $.each(spinners, function(i,spinner) {
      spinner.stop();
    });
    spinners = [];
    $('.btn-basket').removeAttr('disabled');
    $('.btn-basket span').css('opacity','');
    // Render the basket
    basketUi.empty();
    $('.preview-add').show();
    $('.preview-remove').hide();
    $.each(basket, function(i,item) {
      // The API provides only simple IDs right now. Later it should give a detailed object.
      var li = $('<li/>').html('<a href="/dataset/'+item.name+'">'+item.name+'</a>').attr('id',item.id);
      var xButton = $('<button/>').addClass('btn').addClass('btn-small').addClass('x-button').html('x');
      xButton.prependTo(li);
      li.appendTo(basketUi);
      // Update the add/remove buttons on the page
      $('.js-dataset-'+item.id+'-add').hide();
      $('.js-dataset-'+item.id+'-remove').show();
    });
    if (basket.length==0 && basketUiContainer.is(':visible')) {
      basketUiContainer.hide('slow')
    }
    if (basket.length>0 && !basketUiContainer.is(':visible')) {
      basketUiContainer.show('slow')
    }
    basketCache = basket;
  };

  var catchError = function(error) {
    // Recover from errors by fetching the latest authoritative server state
    var endPoint = '/api/2/util/preview_list';
    $.ajax({
      url: endPoint,
      success: renderBasket,
      cache: false
    });
  };

  var clickAdd = function(e) {
    var parent = $(e.target).parents('.map-buttons');
    var packageId = parent.find('.js-data-id').html();
    // Inform the server
    var endPoint = '/api/2/util/preview_list/add/'+packageId;
    $.ajax({
      url: endPoint,
      success: renderBasket,
      error: catchError
    });
    disable();
  };

  var clickRemove = function(e) {
    var parent = $(e.target).parents('.map-buttons');
    var packageId = parent.find('.js-data-id').html();
    var endPoint = '/api/2/util/preview_list/remove/'+packageId;
    $.ajax({
      url: endPoint,
      success: renderBasket,
      error: catchError
    });
    disable();
  };

  var clickReset = function(e) {
    e.preventDefault();
    var endPoint = '/api/2/util/preview_list/reset';
    $.ajax({
      url: endPoint,
      success: renderBasket,
      error: catchError
    });
  };

  var clickX = function(e) {
    var packageId = $(e.target).parents('li').attr('id');
    // Inform the server
    var endPoint = '/api/2/util/preview_list/remove/'+packageId;
    $.ajax({
      url: endPoint,
      success: renderBasket,
      error: catchError
    });
    disable();
  };

  var clickSubmit = function(e) {
    e.preventDefault();
    var href = '/data/map-preview?';
    var extent = {};
    if (basketCache.length) {
      $.each(basketCache, function(i, item) {
        href += item.querystring + '&';
        // Expand extent to include this item's extent
        var item_extent = item.extent;
        $.each('nwes', function(i, direction) {
                 if (extent[direction]) {
                   if (direction == 'n' || direction == 'e') {
                     extent[direction] = Math.max(extent[direction], item_extent[i]);
                   } else {
                     extent[direction] = Math.min(extent[direction], item_extent[i]);
                   }
                 } else {
                   extent[direction] = item_extent[i];
                 }
        });
      });
      if (extent['n'] && extent['w'] && extent['e'] && extent['s']) {
        $.each('nwes', function(i, direction) {
                 if (extent[direction]) {
                   href += '&' + direction + '=' + extent[direction];
                 }
               })
          }
      window.location = href;
    }
  };

  $('.preview-add button').bind('click',clickAdd);
  $('.preview-remove button').bind('click',clickRemove);
  basketSubmitButton.bind('click',clickSubmit);
  basketResetButton.bind('click',clickReset);
  $('#shopping-basket .x-button').live('click', clickX);
  catchError(); // refreshes basket from session
});



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
