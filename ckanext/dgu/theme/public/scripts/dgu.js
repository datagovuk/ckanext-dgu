jQuery(function ($) {

  $(document).ready(function () {
    /* Create javascript tooltips */
    $('.js-tooltip').tooltip();
    $('.js-tooltip-instruction-needed').attr('title', 'Tooltip text required?');
    $('.js-tooltip-instruction-needed').tooltip({'extraClass':'instruction-needed'});

    $('.instruction-needed').tooltip({'extraClass':'instruction-needed'});

    $('.to-be-completed').addClass('js-tooltip-to-be-completed');
    $('.js-tooltip-to-be-completed').tooltip({'extraClass':'to-be-completed'});

    /* Toggle visibility of sub-publishers on the publisher/read.html page */
    $('#sub-publisher-toggle').click(function(){
      $('#sub-publishers li.collapsed').toggle();
    });

    $('input[name="dataset-results-sort"]').change(function(e){
      e.preventDefault();
      window.location = $(this).val()
    });
  });
})

