
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

import logging

from django.utils import simplejson

from common.utilities import as_json
from jobs.models import Job
from jobs import get_worker, get_producer

log = logging.getLogger()

@as_json
def start_job(request):
    # TODO(kumar) check for already running jobs
    # TODO(kumar) run the job reaper
    job_name = request.POST['job_name']
    job = Job(job_name=job_name)
    job.put()
    worker = get_worker(job_name)
    return {
        'job_key': str(job.key()),
        'success': True
    }

@as_json
def do_job_work(request):
    job = Job.get(request.POST['job_key'])
    worker = get_worker(job.job_name)
    finished, result = worker(job.result and simplejson.loads(job.result))
    job.result = simplejson.dumps(result)
    job.save()
    return {
        'finished': finished,
        'success': True
    }