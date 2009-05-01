
jQuery.extend({  
	ajax: function( config ) {
	    var parts = config.url.split('?');
	    var url = parts[0];
	    var qstring = parts[1] || "";
        console.log("Intercepting: " + config.url);
        
        var d = new Date();
        var cur_month = d.getMonth() + 1; // it is zero based
        if (cur_month < 10) {
            cur_month = "0" + cur_month.toString();
        }
        var cur_year = d.getFullYear();
        
        // config.type
        // config.url
        switch (url) {
            case '/chirp/search_users':
                config.success(
                    "Fred Wilson|1\n"+
                    "Francis Barnes|2\n"+
                    "Frida Fremont|3\n"+
                    "Farley Jackson|4\n"+
                    "Frederick Holmes|5\n"+
                    "Fanzo Fananza|6"
                );
                console.log("sent stub search results");
                break;
            case '/chirp/meetings/' + cur_month + '/01/' + cur_year + '/track.json':
                config.success({
                    success:true, 
                    meeting_id:1,
                    attendees:[]
                });
            case '/chirp/meetings/'  + cur_month + '/02/' + cur_year + '/track.json':
                config.success({
                    success:true, 
                    meeting_id:1,
                    attendees:[{
                        user_id:1, name:"Fred Wilson"
                    }, {
                        user_id:2, name:"Francis Barnes"
                    }]
                });
                break;
            case '/chirp/meetings/1/attendee/add/1.json':
            case '/chirp/meetings/1/attendee/add/2.json':
            case '/chirp/meetings/1/attendee/add/3.json':
            case '/chirp/meetings/1/attendee/add/4.json':
            case '/chirp/meetings/1/attendee/add/5.json':
            case '/chirp/meetings/1/attendee/add/6.json':
                config.success({success:true});
                break;
            case '/chirp/meetings/1/attendee/delete/1.json':
            case '/chirp/meetings/1/attendee/delete/2.json':
            case '/chirp/meetings/1/attendee/delete/3.json':
            case '/chirp/meetings/1/attendee/delete/4.json':
            case '/chirp/meetings/1/attendee/delete/5.json':
            case '/chirp/meetings/1/attendee/delete/6.json':
                config.success({success:true});
                break;
            default:
                console.error("Unexpected URL: " + config.url);
        }
	}	
});
    
$(document).ready(function() {    
});