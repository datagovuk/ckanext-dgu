$(function() {

  var basketUi = $('#shopping-basket');
  var basketSubmit = $('#shopping-basket-submit');
  var basket = [];

  var renderBasket = function() {
    basketUi.empty();
    $.each(basket, function(i,item) {
      var li = $('<li/>').html(item.title).attr('id',item.id);
      li.appendTo(basketUi);
    });
    if (basket.length==0) {
      var li = $('<li/>').html("No items").addClass('empty');
      li.appendTo(basketUi);
    }
  };

  var addToBasket = function(id, title) {
    basket.push({
      id: id,
      title: title
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

  var previewAdd = function(e) {
    var parent = $(e.target).parents('.dataset');
    var packageId = parent.find('.js-data-id').html();
    var packageTitle = parent.find('.js-data-title').html();
    addToBasket(packageId,packageTitle);
    // Update my UI
    parent.find('.preview-add').hide();
    parent.find('.preview-remove').show();
    renderBasket();
  };

  var previewRemove = function(e) {
    var parent = $(e.target).parents('.dataset');
    var packageId = parent.find('.js-data-id').html();
    removeFromBasket(packageId);
    // Update my UI
    parent.find('.preview-add').show();
    parent.find('.preview-remove').hide();
    renderBasket();
  };

  var basketSubmit = function(e) {
    console.log(basket);
  };

  $('.preview-add button').bind('click',previewAdd);
  $('.preview-remove button').bind('click',previewRemove);
  basketSubmit.bind('click',basketSubmit);
  renderBasket();
});


