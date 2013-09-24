$(function() {
  var checkboxes = $('.js-compare');
  // Get currently selected IDs
  var one = null;
  var two = null
  checkboxes.prop('checked',false);
  
  function deselect(id) {
    if (id!=one && id!=two) throw ("ID is not selected: "+id);
    $('#checkbox_' +id).prop('checked',false);
    $('#row_' +id).removeClass('selected');
    // Swapping them around gives better UX when deselecting 'one'
    if (id==one) {
      var tmp=one; one=two; two=tmp;
      $('#selected1_'+one).prop('checked',true);
      $('#selected2_'+two).prop('checked',true);
    }
    // Deselect the second option ( assertion: id==two )
    $('#selected2_'+two).prop('checked',false);
    two = null;
  }
  
  function select(id) {
    if (one && two) {
      deselect(two);
    }
    $('#checkbox_'+id).prop('checked',true);
    $('#row_' +id).addClass('selected');
    if (one==null) {
      $('#selected1_'+id).prop('checked',true);
      one = id;
    }
    else {
      $('#selected2_'+id).prop('checked',true);
      two = id;
    }
  }

  function init_selection(index,input) {
    if ($(input).attr('checked')=='checked') {
      var revision_id = $(input).attr('id').split('_')[1];
      select(revision_id);
    }
  }
  // Run these in order
  $.each($('input[name="selected1"]'),init_selection);
  $.each($('input[name="selected2"]'),init_selection);

  // When the user interacts with the checkboxes, toggle the radio buttons
  checkboxes.click(function(e) {
    var target = $(e.target);
    var id = target.attr('id').split('_')[1];
    if (target.prop('checked')) {
      select(id);
    }
    else {
      deselect(id);
    }
  });

});
