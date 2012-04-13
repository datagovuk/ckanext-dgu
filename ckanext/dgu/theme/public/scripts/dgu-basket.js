$(function() {

  var basketUiContainer = $('#shopping-basket-container');
  var basketUi = $('#shopping-basket');
  var basketSubmitButton = $('#shopping-basket-submit');
  var basket = [];

  var renderBasket = function() {
    basketUi.empty();
    $.each(basket, function(i,item) {
      var li = $('<li/>').html(item.title).attr('id',item.id);
      var xButton = $('<button/>').addClass('btn').addClass('btn-small').addClass('x-button').html('x');
      xButton.prependTo(li);
      li.appendTo(basketUi);
    });
    if (basket.length==0 && basketUiContainer.is(':visible')) {
      basketUiContainer.hide('slow')
    }
    if (basket.length>0 && !basketUiContainer.is(':visible')) {
      basketUiContainer.show('slow')
    }
  };

  var addToBasket = function(id, title, querystring) {
    basket.push({
      id: id,
      title: title,
      querystring: querystring
    });
  };
  var removeFromBasket = function(id) {
    var index = -1;
    $.each(basket, function(i,item) {
      if (item.id == id) {
        index = i;
      }
    });
    if (index==-1) throw "Item not found.";
    basket.splice(index,1);
  };

  var clickAdd = function(e) {
    var parent = $(e.target).parents('.dataset');
    var packageId = parent.find('.js-data-id').html();
    var packageTitle = parent.find('.js-data-title').html();
    var packageQuerystring = parent.find('.js-data-querystring').html();
    addToBasket(packageId,packageTitle,packageQuerystring);
    // Trial animation
    /*
    var fromImg = parent.find('.preview-add img');
    var from = fromImg.offset();
    var to = basketUi.offset();
    to.left += (basketUi.width() / 2)-20;
    to.top += (basketUi.height() / 2)-20;
    to.opacity = 0.75;
    var img = $('<img/>').attr('src','/images/compass.png').css({ 'position':'absolute' }).css(from);
    img.appendTo($('body'));
    img.animate(to, 800, "easeOutCubic", function() {
      img.animate({'opacity':0}, 200, "linear", function() {
        img.remove();
      });
    });
    */
    // Update my UI
    parent.find('.preview-add').hide();
    parent.find('.preview-remove').show();
    /*
    var endPoint = '/api/2/util/preview_list/add/'+packageId;
    $.ajax({
      url: endPoint,
      success: function(data) { 
        console.log(data);
      }
    });
    */
    renderBasket();
  };

  var clickRemove = function(e) {
    var parent = $(e.target).parents('.dataset');
    var packageId = parent.find('.js-data-id').html();
    removeFromBasket(packageId);
    // Update my UI
    parent.find('.preview-add').show();
    parent.find('.preview-remove').hide();
    renderBasket();
  };
  
  var clickX = function(e) {
    var id = $(e.target).parents('li').attr('id');
    // Find the button within the page
    var mainButton = $('.js-dataset-'+id+' .preview-remove button');
    if (mainButton.length) {
      mainButton.click();
    }
    else {
      removeFromBasket(id);
      renderBasket();
    }
  };

  var clickSubmit = function(e) {
    e.preventDefault();
    var href = $(e.target).attr('href');
    if (basket.length) {
      $.each(basket, function(i, item) {
        href += item.querystring + '&';
      });
      window.location = href;
    }
  };

  $('.preview-add button').bind('click',clickAdd);
  $('.preview-remove button').bind('click',clickRemove);
  basketSubmitButton.bind('click',clickSubmit);
  renderBasket();
  $('#shopping-basket .x-button').live('click', clickX);
});


