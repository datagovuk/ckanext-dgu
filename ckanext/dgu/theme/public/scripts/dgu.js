jQuery(function ($) {

  $(document).ready(function () {
    /* Create javascript tooltips */
    $('.js-tooltip').tooltip();
    $('.js-tooltip-instruction-needed').attr('title', 'Tooltip text required?');
    $('.js-tooltip-instruction-needed').tooltip({'extraClass':'instruction-needed'});

    $('.instruction-needed').tooltip({'extraClass':'instruction-needed'});

    $('.to-be-completed').addClass('js-tooltip-to-be-completed');
    $('.js-tooltip-to-be-completed').tooltip({'extraClass':'to-be-completed'});
    
  });
})