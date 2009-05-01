
// silent logging when Firebug is not active:
if ( ! window.console ) {
    window.console = {
		log: function(){},
		debug: function(){},
		info: function(){},
		warn: function(){},
		error: function(){},
		assert: function(truth, message){},
		dir: function(obj){},
		dirxml: function(node){},
		trace: function(){},
		profile: function(){},
		profileEnd: function(){ },
		clear: function(){},
		open: function(){},
		close: function(){}
	};
}

chirp = {};
chirp.error = function(err_info) {
    // err_info = {
    //     'error': '',
    //     'traceback': '',     
    // }
    console.log(err_info.traceback);
    console.log(err_info.error);
};
chirp.url = function(relative_path) {
    // this exists for UI tests replace
    return "/" + relative_path;
};
chirp.request = function(config) {
    return $.ajax({
        type: config.type || 'GET',
        url: config.url,
        data: config.data || {},
        dataType: config.dataType || 'json',
        success: config.success,
        error: config.error || function(xhr, ajaxOptions, thrownError) {
            console.log(xhr);
            console.log(ajaxOptions);
            console.log(thrownError);
            // chirp.error();
            
            // *sigh*, I'm not sure how to get the actual error message out of this just yet.
            alert("Whoops, an unexpected error happened on the server.  " + 
                  "Please alert someone so he/she can check the logs.");
        }
    });
};