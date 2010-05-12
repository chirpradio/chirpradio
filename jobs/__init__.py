
"""Execute long running jobs incrementally in multiple requests. 

App Engine has pretty strict time limits which means it's really hard to do things like build reports that need to query data over a period of a month or so when the data set is large.  This provides a framework for running these kinds of jobs.

First you need webpage that can interact with the job server.  In jQuery it looks something like this::
    
    
    $.post({
        url: '/jobs/start',
        data: {
            'job_key': 'build-playlist-report'
        },
        dataType: 'json',
        success: function(data, textStatus) {
            job_id = data.job_id;
            work(job_id);
        }
    });
    
    var work = function(job_id) {
        $.post({
            url: '/jobs/work',
            data: {
                'job_id': job_id
            },
            dataType: 'json',
            success: function(data, textStatus) {
                if (data.done) {
                    show_product(job_id)
                } else {
                    work(job_id);
                }
            }
        });
    };
    
    var show_product = function(job_id) {
        $("#ready-link").html('<a href="/jobs/product/' + job_id + '">Download CSV</a>');
    };

On the server, all you have to do is implement a worker method::
    
    from jobs import job_worker, job_product
    
    @job_worker('build-playlist-report')
    def playlist_report_worker(results):
        if results is None:
            # build report headers:
            results = {
                'file_lines': ["date, employee, hair_color"],
                'last_offset': 0
            }
        
        offset = results['last_offset]
        last_offset = offset+10
        results['last_offset'] = last_offset
        
        got_rows = False
        for employee in Employee.all()[ offset: last_offset ]:
            got_rows = True
            results['file_lines'].append(",".join([
                    str(datetime.datetime.now()),
                    employee.name,
                    employee.hair_color
                ]))
        
        if not got_rows:
            finished = True
        else:
            finished = False
        
        return finished, results
    
    @job_product('build-playlist-report')
    def playlist_report_product(results):
        csv_file = "\n".join(results['file_lines'])
        # respond with the CSV file...
        
"""