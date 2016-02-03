
    function reset_names() {
        // Reset all of the hidden field names
        var number = 0;
        $('#datasets div.row').each(function(elem){
            var newname = 'packages__' + number + '__name';
            $(this).find('input').attr('name', newname);
            number = number + 1;
        });
    }

    function add_dataset(item) {
        var t = $('#row-template').html();
        t = t.replace(/&lt;%name\%&gt;/g, item.value)
            .replace(/&lt;%title%&gt;/g, item.label)
            .replace(/<%name%>/g, item.value);
        console.log(t)
        $('#datasets').append(t);
        reset_names();
    }

$(function() {
    new CKAN.Dgu.UrlEditor({slugType:'group'});

    $('.package-typeahead').autocomplete({source: function (request, response) {
        jQuery.get("/api/util/dataset/autocomplete", {
            incomplete: request.term,
            limit: 10
            },
            function (data) {
                var arr = new Array();
                for ( var i = 0; i < data.ResultSet.Result.length; i++ ) {
                    var lbl = data.ResultSet.Result[i].title + " (" + data.ResultSet.Result[i].name + ")";
                    arr.push({label: lbl, value: data.ResultSet.Result[i].name})
                }
                response(arr);});
            }, items:5});

            $( ".package-typeahead" ).autocomplete({
                select: function( event, ui ) {
                add_dataset(ui.item);
                $(this).val("");
                return false;
            }
    });
});
