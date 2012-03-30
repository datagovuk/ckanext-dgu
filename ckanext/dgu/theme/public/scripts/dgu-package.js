var container = $('#comments');
$.ajax({
        url: '/comment/get/3266d22c-9d0f-4ebe-b0bc-ea622f858e15',
        data: '',
        dataType: 'html',
        success: function(data, textStatus, xhr) {
          container.html(data);
        },
        error: function(xhr, status, exception) {
          container.html('There has been an error');
        }
      });
