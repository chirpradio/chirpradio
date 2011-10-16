$(document).ready(function() {
    $("input.reviewed_checkbox").change(function() {
        var url = window.location.pathname + '?';
        var parts = window.location.href.split('?');
        if (this.checked) {
            if (parts.length > 1) {
                params = parts[1].split('&');
                for (var i = 0; i < params.length; i++) {
                    var nameVal = params[i].split('=');
                    if (nameVal[0] != "reviewed") {
                        if (i > 0)
                            url += '&';
                        url += params[i];
                    }
                }
                url += '&';
            }
            url += 'reviewed=true';
        }
        else {
            params = parts[1].split('&');
            for (i = 0; i < params.length; i++) {
                nameVal = params[i].split('=');
                if (nameVal[0] != "reviewed") {
                    if (i > 0)
                        url += '&';
                    url += params[i];
                }
            }
        }
        window.location = url;
    });
    
    $('#id_reviewed').click(function(e) {
        if ($(this).is(':checked')) {
            $('#id_not_reviewed').attr('checked', false);
        }
    });
    $('#id_not_reviewed').click(function(e) {
        if ($(this).is(':checked')) {
            $('#id_reviewed').attr('checked', false);
        }
    });

});
