$(function() {
      var osPrefix = 'http://clients.openspending.org/data.gov.uk/openspendingjs/';
      OpenSpending.scriptRoot = osPrefix;
      OpenSpending.localeGroupSeparator = ",";
      OpenSpending.localeDecimalSeparator = ".";
      var b = new OpenSpending.Browser(
        "#openspending_browser",
        "ukgov-25k-spending",
        {'source': 'https://openspending.org'}
      );
      b.init();

      // Limited length of sidebars
      var sidebar = $('.browser_faceter');
      function limitTableLength(table) {
          if (table.hasClass('trimmed')) { return; }
          $.each(table.find('tr'), function(i, row) {
              // Hide all rows beyond a certain point
              if (i<5) { return; }
              $(row).hide();
          });
          table.addClass('trimmed');
          var moreButton = $('<a href="#" class="more-button openspending-more-button" />').text('[more]');
          moreButton.insertAfter(table);
          moreButton.on('click',function(e) {
              e.preventDefault();
              $.each(table.find('tr'), function(i,row) {
                  $(row).show('slow');
              });
              table.removeClass('trimmed');
              moreButton.remove();
              return false;
          });
      }

      function onRedrawSidebar(e) {
          $.each(sidebar.find('table.facets'), function(i,table) {
              var length = $(table).find('tr').length;
              if (length>=8) { limitTableLength($(table)); }
          });
      }

      function initPagination(e){
        $('.pagination ul').addClass('pagination');
        $('.pagination').parent().addClass('dgu-pagination');
      }

      sidebar.on('faceter:init faceter:addFilter faceter:removeFilter', onRedrawSidebar);
      sidebar.on('faceter:init', initPagination);
});
