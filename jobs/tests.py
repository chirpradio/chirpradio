
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

from django.test import TestCase as DjangoTestCase
from django.core.urlresolvers import reverse
from django.utils import simplejson

from auth import roles
import jobs
from jobs.models import Job
from jobs import worker_registry, job_worker

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
    
class TestJobWorker(DjangoTestCase):
    
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
    