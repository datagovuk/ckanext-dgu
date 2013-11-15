$(function() {
  var bind = $('.js-trigger-publisher-scroll');
  bind.on('shown.bs.dropdown',function() {
    var h = $('.publisher-dropdown');
    if (h.height()>450) {
      h.scrollTop(0);
      var r = h.find('.publisher-row.active');
      var top = r.position().top - 300;
      h.scrollTop(top);
    }
  });
});
