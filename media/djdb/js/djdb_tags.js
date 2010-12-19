$(document).ready(function() {
    $('img.add_tag').click(function(event) {
        $('.tags').append($('select.tag'));
        $('select.tag option:first').attr("selected", true)
        $('select.tag').show();
        event.stopImmediatePropagation();
    });
    
    $('select.tag').change(function(event) {
        var tagName = $('select.tag option:selected').text()
        
        if (tagName == 'Other') {
            $('.tags').append($('input.tag'));
            $('input.tag').attr('value', '');
            $('input.tag').show();
            $('input.tag').focus();
        }
        else {
            // Hide other tag text box.
            $('input.tag').hide();
            
            // Append the new tag to the visible list.
            $('.tags').append('<div class="tag">'
                              + tagName
                              + '<img class="remove_tag" style="display: none" src="/media/common/img/remove.png" title="Remove tag"/>'
                              + '</div>');
            
            // Remove entry from select list.
            $('select.tag option:selected').remove();
            
            // Hide the tags combo box.
            $(this).hide();
            
            // Get album id from url and add new tag.
            var parts = window.location.pathname.split('/');
            var albumId = parts[parts.length - 2];
            $.get('/djdb/album/' + albumId + '/add_tag?tag=' + tagName);
        }
        
        event.stopImmediatePropagation();
    });
    
    $('input.tag').keyup(function(event) {
        if (event.keyCode == 13) {
            var tagName = $(this).val();
            
            // Hide other tag text box.
            $(this).hide();
            
            // Append the new tag to the visible list.
            $('.tags').append('<div class="tag">'
                              + tagName
                              + '<img class="remove_tag" style="display: none" src="/media/common/img/remove.png" title="Remove tag"/>'
                              + '</div>');
            
            // Hide the tags combo box.
            $('select.tag').hide();
            
            // Get album id from url and add new tag.
            var parts = window.location.pathname.split('/');
            var albumId = parts[parts.length - 2];
            $.get('/djdb/album/' + albumId + '/add_tag?tag=' + tagName);
        }
        
        event.stopImmediatePropagation();
    });
    
    $('div.tag').live('mouseover', function(event) {
        $(this).find('img.remove_tag').show();
    });
    $('div.tag').live('mouseout', function() {
        $(this).find('img.remove_tag').hide();
    });
    
    $('img.remove_tag').live('click', function(event) {
        var tagName = $(this).parent().text().trim();
        
        $(this).parent().remove();
        
        // Get album id from url and remove tag.
        var parts = window.location.pathname.split('/');
        var albumId = parts[parts.length - 2];
        //$.get('/djdb/album/' + albumId + '/remove_tag?tag=' + tagName);
        $.ajax({
            url: '/djdb/album/' + albumId + '/remove_tag?tag=' + tagName,
            type: 'GET',
            error: function(data) {
                $('div.error').append(data.responseText);
            }
        });
        
        // Insert tag into select list.
        var last = true;
        $('select.tag option').each(function(index) {
            if (tagName == $(this).text()) {
                last = false;
                return false;
            }
            else if ($(this).text() != '-' && $(this).text() != 'Other'
                     && tagName < $(this).text()) {
                $(this).before('<option>' + tagName + '</option>');
                last = false;
                return false;
            }
        });
        if (last) {
            $('select.tag').append('<option>' + tagName + '</option>');
        }
        
        event.stopImmediatePropagation();
        return false;
    });
});
