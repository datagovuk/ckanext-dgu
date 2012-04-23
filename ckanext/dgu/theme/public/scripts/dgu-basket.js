
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
      var li = $('<li/>').html(item.name).attr('id',item.id);
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
      success: renderBasket
    });
  };

  var clickAdd = function(e) {
    var parent = $(e.target).parents('.dataset');
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
    var parent = $(e.target).parents('.dataset');
    var packageId = parent.find('.js-data-id').html();
    // Pass the function call through to the X button in the basket
    basketUi.find('#'+packageId+' .x-button').click();
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
    if (basketCache.length) {
      $.each(basketCache, function(i, item) {
        href += item.querystring + '&';
      });
      window.location = href;
    }
  };

  $('.preview-add button').bind('click',clickAdd);
  $('.preview-remove button').bind('click',clickRemove);
  basketSubmitButton.bind('click',clickSubmit);
  basketResetButton.bind('click',clickReset);
  $('#shopping-basket .x-button').live('click', clickX);
  renderBasket(preloadBasket);
});


