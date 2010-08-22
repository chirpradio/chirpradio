
###
### Copyright 2010 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the 'License');
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an 'AS IS' BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

"""Execute long running jobs incrementally in multiple requests. 

App Engine has very strict execution time limits so it's really hard to do things like build reports that need to query data over a period of a month or so when the data set is large.  This provides a framework for running these kinds of jobs.

First you need webpage that can interact with the job server.  In jQuery it looks something like this::
    
    
    $.ajax({
        type: 'POST',
        url: '/jobs/start',
        data: {
            'job_name': 'build-playlist-report'
        },
        dataType: 'json',
        success: function(result, textStatus) {
            job_key = result.job_key;
            work(job_key);
        }
    });
    
    var work = function(job_key) {
        $.ajax({
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

On the server, all you have to do is implement a worker method::
    
    from jobs import job_worker, job_product
    
    @job_worker('build-playlist-report')
    def playlist_report_worker(results, request_params):
        if results is None:
            # build report headers:
            results = {
                'file_lines': ["date, employee, hair_color"],
                'last_offset': 0
            }
        
        offset = results['last_offset']
        last_offset = offset+10
        results['last_offset'] = last_offset
        
        got_results = False
        for employee in Employee.all()[ offset: last_offset ]:
            got_results = True
            results['file_lines'].append(",".join([
                    str(datetime.datetime.now()),
                    employee.name,
                    employee.hair_color
                ]))
        
        if not got_results:
            finished = True
        else:
            finished = False
        
        return finished, results
    
    @job_product('build-playlist-report')
    def playlist_report_product(results):
        csv_file = "\n".join(results['file_lines'])
        # respond with the CSV file...
        
"""

worker_registry = {}

def _reset_registry():
    worker_registry['workers'] = {}
    worker_registry['producers'] = {}

_reset_registry()

def job_product(job_name):
    def fn_decorator(fn):
        worker_registry['producers'][job_name] = fn
        return fn
    return fn_decorator

def job_worker(job_name):
    def fn_decorator(fn):
        worker_registry['workers'][job_name] = fn
        return fn
    return fn_decorator

def get_worker(job_name):
    if job_name not in worker_registry['workers']:
        raise LookupError("No worker has been registered for job %r" % job_name)
    return worker_registry['workers'][job_name]

def get_producer(job_name):
    if job_name not in worker_registry['producers']:
        raise LookupError("No producer has been registered for job %r" % job_name)
    return worker_registry['producers'][job_name]
