// requires: chirp/chirp.js
//           

chirp.traffic_log_report = {};

$(document).ready(function() {
    
    $("#download").click(function(event) {
        event.preventDefault();
        var values = {};
        $.each($('.contents form').serializeArray(), function(i, field) {
            values[field.name] = field.value;
        });
        
        chirp.request({
            type: 'POST',
            url: '/jobs/start',
            data: {
                'job_name': 'build-trafficlog-report'
            },
            dataType: 'json',
            success: function(result, textStatus) {
                job_key = result.job_key;
                console.log("starting work on job key", job_key);
                work(job_key);
            }
        });
    });
    
    var work = function(job_key) {
        console.log("working...");
        chirp.request({
            type: 'POST',
            url: '/jobs/work',
            data: {
                'job_key': job_key
            },
            dataType: 'json',
            success: function(job_result, textStatus) {
                if (job_result.finished) {
                    show_product(job_key)
                } else {
                    work(job_key);
                }
            }
        });
    };
    
    var show_product = function(job_key) {
        $("#ready-link").html('<a href="/jobs/product/' + job_key + '">Download CSV</a>');
    };
});