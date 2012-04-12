$(function() {

  var basketUi = $('#shopping-basket');
  var basketSubmit = $('#shopping-basket-submit');

  var previewAdd = function(e) {
    e.preventDefault();
    var parent = $(e.target).parents('.dataset');
    var packageId = parent.find('.js-data-id').html();
    var packageTitle = parent.find('.js-data-title').html();
    var li = $('<li/>').addClass('entry').html(packageTitle).attr('id',packageId);
    // Add an entry to the shopping basket
    if (!basketUi.find('#'+packageId).length) {
      li.appendTo(basketUi);
    }
    basketUi.find('.empty').hide();
  };

  var basketSubmit = function(e) {
    e.preventDefault();
    var ids = [];
    $.each(basketUi.find('.entry'), function(i, li) {
      ids.push( li.attr('id') );
    });
    console.log(ids);
  };

  $('.preview-add').bind('click',previewAdd);
  basketSubmit.bind('click',basketSubmit);
});


