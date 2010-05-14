
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

from auth import roles
import jobs
from jobs.models import Job
from jobs import worker_registry, job_worker, job_product

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
    
class TestJobs(DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
        
        @job_worker('counter')
        def counter(data):
            if data is None:
                data = {'count':0}
            data['count'] += 1
            
            if data['count'] == 3:
                finished = True
            else:
                finished = False
                
            return finished, data
    
    def tearDown(self):
        teardown_data()
    
    def assert_json_success(self, json_response):
        self.assertEqual(json_response['success'], True,
                    "Unsuccessful response, error=%r" % json_response.get('error'))
    
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
