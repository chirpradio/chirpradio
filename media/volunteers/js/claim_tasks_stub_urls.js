
jQuery.extend({  
	ajax: function( config ) {
	    var parts = config.url.split('?');
	    var url = parts[0];
	    var qstring = parts[1] || "";
        console.log("Intercepting: " + config.url);
        
        switch (url) {
            case '/chirp/tasks/claim/1.json':
            case '/chirp/tasks/claim/2.json':
            case '/chirp/tasks/claim/3.json':
            case '/chirp/tasks/claim/4.json':
                config.success({
                    success: true, 
                    user: {first_name:"Willy", last_name:"McLovin"}
                });
                break;
            default:
                console.error("Unexpected URL: " + config.url);
        }
	}	
});
