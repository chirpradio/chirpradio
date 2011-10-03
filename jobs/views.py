
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
import datetime
from datetime import timedelta
import traceback

from django.conf import settings
from django.utils import simplejson
from django.http import Http404

from common.utilities import as_json
from jobs.models import Job
from jobs import get_worker, get_producer

log = logging.getLogger()


def init_jobs():
    # TODO(Kumar) figure out a better way to register job workers.
    # This is currently necessary because app warmup isn't fast enough
    # to catch process restarts.
    for path in settings.JOB_WORKER_MODULES:
         __import__(path)  # registers the job workers


def reap_dead_jobs():
    q = Job.all().filter("started <",
                         datetime.datetime.now() - timedelta(days=2))
    for job in q:
        job.delete()


def start_job(request):
    init_jobs()
    # TODO(kumar) check for already running jobs
    reap_dead_jobs()
    job_name = request.POST['job_name']
    job = Job(job_name=job_name)
    job.put()
    worker = get_worker(job_name)
    if worker['pre_request']:
        early_response = worker['pre_request'](request)
        if early_response is not None:
            return early_response
    @as_json
    def data(request):
        return {
            'job_key': str(job.key()),
            'success': True
        }
    return data(request)


def do_job_work(request):
    init_jobs()
    try:
        job = Job.get(request.POST['job_key'])
        params = request.POST.get('params', '{}')
        worker = get_worker(job.job_name)
        if worker['pre_request']:
            early_response = worker['pre_request'](request)
            if early_response is not None:
                return early_response
        if job.result:
            result_for_worker = simplejson.loads(job.result)
        else:
            result_for_worker = None
        finished, result = worker['callback'](result_for_worker,
                                              simplejson.loads(params))
        job.result = simplejson.dumps(result)
        job.save()
    except:
        traceback.print_exc()
        raise
    @as_json
    def data(request):
        return {
            'finished': finished,
            'success': True
        }
    return data(request)


def get_job_product(request, job_key):
    init_jobs()
    job = Job.get(job_key)
    if job is None:
        raise Http404(
            "The requested job product does not exist.  It may have expired, "
            "in which case you will have to run the job again.")
    # TODO(kumar) make sure job is finished
    producer = get_producer(job.job_name)
    if producer['pre_request']:
        early_response = producer['pre_request'](request)
        if early_response is not None:
            return early_response
    result = simplejson.loads(job.result)
    return producer['callback'](result)
