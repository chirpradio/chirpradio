// requires: chirp/chirp.js
//           json2.js

chirp.traffic_log_report = {};

$(document).ready(function() {
    
    $("#download").click(function(event) {
        event.preventDefault();
        $("#ready-link").html('');
        $("#ready-link").addClass('report-loading');
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
                work(job_key, values);
            }
        });
    });
    
    var work = function(job_key, form_values) {
        chirp.request({
            type: 'POST',
            url: '/jobs/work',
            data: {
                'job_key': job_key,
                'params': JSON.stringify(form_values)
            },
            dataType: 'json',
            success: function(job_result, textStatus) {
                if (job_result.finished) {
                    show_product(job_key);
                } else {
                    work(job_key, form_values);
                }
            }
        });
    };
    
    var show_product = function(job_key) {
        $("#ready-link").removeClass('report-loading');
        $("#ready-link").html('<a href="/jobs/product/' + job_key + '">Download CSV</a>');
    };
});