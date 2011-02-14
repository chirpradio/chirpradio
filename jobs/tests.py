
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

from unittest import TestCase
import datetime
from datetime import timedelta

from django.test import TestCase as DjangoTestCase
from django.core.urlresolvers import reverse
from django.utils import simplejson
from django import http
from nose.tools import eq_

from auth import roles
import jobs
from jobs.models import Job
from jobs import worker_registry, job_worker, job_product


_worker_registry = {}


def setup():
    _worker_registry.update(jobs.worker_registry)


def teardown():
    jobs.worker_registry.update(_worker_registry)


class JobTestCase(object):
    """Mixin for tests that use jobs/workers."""

    def get_job_product(self, job_name, params):
        """Simulates the requests made by JavaScript code 
        to get the final job product.
        """
        r = self.client.post(reverse('jobs.start'),
                             data={'job_name': 'build-trafficlog-report'})
        eq_(r.status_code, 200)
        job = simplejson.loads(r.content)
        done = False
        attempts = 0
        while not done:
            attempts += 1
            if attempts > 30:
                raise RuntimeError(
                        "Job %r did not finish after %s attempts" % (
                                                    job_name, attempts))
            r = self.client.post(reverse('jobs.work'),
                                 data={'job_key': job['job_key'],
                                       'params': simplejson.dumps(params)})
            eq_(r.status_code, 200)
            work = simplejson.loads(r.content)
            done = work['finished']
        # TODO(kumar) check work['success']
        r = self.client.post(reverse('jobs.product', args=[job['job_key']]))
        eq_(r.status_code, 200)
        return r


def teardown_data():
    for ob in Job.all():
        ob.delete()
    jobs._reset_registry()

class TestJobModel(TestCase):
    
    def test_start_job(self):
        job = Job(job_name='name-of-job')
        self.assertEqual(
            job.started.timetuple()[0:4], 
            datetime.datetime.now().timetuple()[0:4])
        self.assertEqual(job.finished, None)
        self.assertEqual(job.result, None)
    
    def tearDown(self):
        teardown_data()

class JobSelfTestCase(DjangoTestCase):
    
    def tearDown(self):
        teardown_data()
    
    def assert_json_success(self, json_response):
        self.assertEqual(json_response['success'], True,
                    "Unsuccessful response, error=%r" % json_response.get('error'))
    
class TestJobs(JobSelfTestCase):
    
    def setUp(self):
        assert self.client.login(email="test@test.com", roles=[roles.DJ])
        
        @job_worker('counter')
        def counter(data, request_params):
            if data is None:
                data = {'count':0}
            data['count'] += 1
            
            if data['count'] == 3:
                finished = True
            else:
                finished = False
                
            return finished, data
    
    def test_start(self):
        response = self.client.post(reverse('jobs.start'), {
            'job_name': 'counter'
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        
        job = Job.all().filter('job_name =', 'counter')[0]
        self.assertEqual(json_response['job_key'], str(job.key()))
        self.assertEqual(job.result, None)
    
    def test_do_work(self):
        response = self.client.post(reverse('jobs.start'), {
            'job_name': 'counter'
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        job_key = json_response['job_key']
        
        # work the counter three times:
        response = self.client.post(reverse('jobs.work'), {
            'job_key': job_key
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        job = Job.all().filter('job_name =', 'counter')[0]
        self.assertEqual(simplejson.loads(job.result), {'count':1})
        self.assertEqual(json_response['finished'], False)
        
        response = self.client.post(reverse('jobs.work'), {
            'job_key': job_key
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        job = Job.all().filter('job_name =', 'counter')[0]
        self.assertEqual(simplejson.loads(job.result), {'count':2})
        self.assertEqual(json_response['finished'], False)
        
        response = self.client.post(reverse('jobs.work'), {
            'job_key': job_key
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        job = Job.all().filter('job_name =', 'counter')[0]
        self.assertEqual(simplejson.loads(job.result), {'count':3})
        self.assertEqual(json_response['finished'], True)
    
    def test_get_job_product(self):
        
        @job_product('counter')
        def counter_product(data):
            content = "Count is: %s" % data['count']
            return http.HttpResponse(content=content, status=200)
            
        response = self.client.post(reverse('jobs.start'), {
            'job_name': 'counter'
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        job_key = json_response['job_key']
        
        # count three times until finished:
        response = self.client.post(reverse('jobs.work'), {
            'job_key': job_key
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        
        response = self.client.post(reverse('jobs.work'), {
            'job_key': job_key
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        
        response = self.client.post(reverse('jobs.work'), {
            'job_key': job_key
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        
        # get the product:
        response = self.client.get(reverse('jobs.product', args=(job_key,)))
        self.assertEqual(response.content, "Count is: 3")
    
    def test_get_nonexistant_job_product(self):
        # make a deleted job:
        job = Job(job_name="counter")
        job.save()
        job_key = job.key()
        job.delete()
        
        response = self.client.get(reverse('jobs.product', args=(job_key,)))
        self.assertEqual(response.status_code, 404)
    
    def test_job_reaper_kills_old_jobs(self):
        # make an old job:
        job = Job(job_name='counter')
        job.started = datetime.datetime.now() - timedelta(days=3)
        job.save()
        old_job_key = job.key()
        
        response = self.client.post(reverse('jobs.start'), {
            'job_name': 'counter'
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        
        self.assertEqual(Job.get(old_job_key), None)

    
class TestJobsWithParams(JobSelfTestCase):
    
    def setUp(self):
        assert self.client.login(email="test@test.com", roles=[roles.DJ])
        
        @job_worker('report')
        def report_worker(data, request_params):
            if data is None:
                data = {
                    'file_lines': []
                }
            
            data['file_lines'].append(
                "Results from %s to %s" % (
                    request_params['start_date'],
                    request_params['end_date']
                )
            )
            
            finished = True
            return finished, data
        
        @job_product('report')
        def report_product(data):
            content = "".join(data['file_lines'])
            return http.HttpResponse(content=content, status=200)
    
    def test_run_job_with_params(self):
        
        # start the job
        response = self.client.post(reverse('jobs.start'), {
            'job_name': 'report'
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        job_key = json_response['job_key']
        
        # run the job...
        response = self.client.post(reverse('jobs.work'), {
            'job_key': job_key,
            'params': simplejson.dumps({
                'start_date': '2010-08-01',
                'end_date': '2010-08-31'
            })
        })
        json_response = simplejson.loads(response.content)
        self.assert_json_success(json_response)
        
        # get the product:
        response = self.client.get(reverse('jobs.product', args=(job_key,)))
        self.assertEqual(response.content,
                         "Results from 2010-08-01 to 2010-08-31")

    
class TestAccessRestriction(JobSelfTestCase):
    
    def setUp(self):
        assert self.client.login(email="test@test.com", roles=[roles.DJ])
        
        def restricted(request):
            assert isinstance(request, http.HttpRequest)
            return http.HttpResponseForbidden('no access')
        
        @job_worker('some-job', pre_request=restricted)
        def _worker(data, request_params):
            return data
        
        @job_product('some-job', pre_request=restricted)
        def _product(data):
            return http.HttpResponse('<product>')
    
    def test_start(self):
        response = self.client.post(reverse('jobs.start'), {
            'job_name': 'some-job'
        })
        self.assertEqual(response.status_code, 403)
    
    def test_work(self):
        job = Job(job_name='some-job')
        job.put()
        response = self.client.post(reverse('jobs.work'), {
            'job_key': str(job.key()),
            'params': '{}'
        })
        self.assertEqual(response.status_code, 403)
    
    def test_product(self):
        job = Job(job_name='some-job')
        job.put()
        response = self.client.get(reverse('jobs.product',
                                   args=[str(job.key())]))
        self.assertEqual(response.status_code, 403)
