(function ($) {
  $(document).ready(function () {
    CKAN.Dgu.setupPublisherUserAutocomplete($('input.autocomplete-publisher-user'));
    CKAN.Dgu.setupPackageAutocomplete($('input.autocomplete-dataset'));
  });
}(jQuery));

var CKAN = CKAN || {};

CKAN.Dgu = function($, my) {
  my.stub = function() {}


 my.setupPublisherUserAutocomplete = function(elements) {
    elements.autocomplete({
      minLength: 2,
      source: function(request, callback) {
        var url = '/api/2/util/user/autocomplete?q=' + request.term;
        $.getJSON(url, function(data) {
          $.each(data, function(idx, userobj) {
            var label = '';userobj.name;
            if (userobj.fullname) {
              label += userobj.fullname;
            }
            label += ' [' + userobj.name + ']';
            userobj.label = label;
            userobj.value = userobj.name;
          });
          callback(data);
        });
      },
       select: function(event, ui) {
        var input_box = $(this);
        input_box.val('');
           var added_users = $('.added-users');
        var old_name = input_box.attr('name');
        var field_name_regex = /^(\S+)__(\d+)__(\S+)$/;
        var split = old_name.match(field_name_regex);

        var new_name = split[1] + '__' + (parseInt(split[2]) + 1) + '__' + split[3]
        input_box.attr('name', new_name)
        input_box.attr('id', new_name)

        var capacity = $("input:radio[name=add-user-capacity]:checked").val();
        added_users.after(
          '<input type="hidden" name="' + old_name + '" value="' + ui.item.value + '">' +
          '<input type="hidden" name="' + old_name.replace('__name','__capacity') + '" value="' + capacity + '">' +
          '<dd>' + ui.item.label + '</dd>'
        );

        return false; // to cancel the event ;)
      }
    });
  };

  my.setupPackageAutocomplete = function(elements) {
    elements.autocomplete({
      minLength: 0,
      source: function(request, callback) {
        var url = '/api/util/dataset/autocomplete?q=' + request.term;
        $.ajax({
          url: url,
          success: function(data) {
            // atm is a string with items broken by \n and item = title (name)|name
            var out = [];
            var items = data.split('\n');
            $.each(items, function(idx, value) {
              var _tmp = value.split('|');
              var _newItem = {
                label: _tmp[0],
                value: _tmp[1]
              };
              out.push(_newItem);
            });
            callback(out);
          }
        });
      }
      , select: function(event, ui) {
        var input_box = $(this);
        input_box.val('');
          var added_users = $('.added-users');
        var old_name = input_box.attr('name');
        var field_name_regex = /^(\S+)__(\d+)__(\S+)$/;
        var split = old_name.match(field_name_regex);

        var new_name = split[1] + '__' + (parseInt(split[2]) + 1) + '__' + split[3]

        input_box.attr('name', new_name)
        input_box.attr('id', new_name)

        added_users.after(
          '<input type="hidden" name="' + old_name + '" value="' + ui.item.value + '">' +
          '<dd>' + ui.item.label + '</dd>'
        );
      }
    });
  };
  return my;
}(jQuery, CKAN.Dgu || {});
