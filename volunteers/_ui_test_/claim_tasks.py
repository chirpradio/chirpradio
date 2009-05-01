
"""This is a stub view that can be used to 
develop or test the Claim Tasks screen
without hitting the actual database.

"""

import datetime
from django.template import Context, loader
from django.http import HttpResponse
from chirp.utils import as_json

class StubObject(object):
    """a generic object with properties to simulate a database model instance."""
    
    def __init__(self, **kw):
        self.__dict__.update(kw)

class Event(StubObject):
    pass

class Task(StubObject):
    pass

class TaskType(StubObject):
    pass

def claim_tasks_dev(request):
    t = loader.get_template('claim_tasks.html')
    c = Context({
        'extra_js_scripts': [
            '/local_site_media/js/chirp/claim_tasks_stub_urls.js'
        ],
        
        'events': [
            Event(
                name='Chirp Record Fair And Other Delights',
                tasks=[
                    Task(
                        id=1,
                        claim_task_url="/chirp/tasks/claim/1.json",
                        task_type=TaskType(
                            short_description="Tabling",
                            description="Selling records, talking up CHIRP, etc."),
                        start_time=datetime.datetime(2009,4,18,12),
                        end_time=datetime.datetime(2009,4,18,14),
                        num_volunteers_needed=2,
                        claim_prompt=(
                            "You are about to commit to Tabling on Sat Apr 18th "
                            "from 12:00 p.m. - 2:00 p.m."),
                        claimed_by=[StubObject(first_name="Bob",last_name="Willis")]),
                    Task(
                        id=2,
                        claim_task_url="/chirp/tasks/claim/2.json",
                        task_type=TaskType(
                            short_description="Tabling",
                            description="Not shown"),
                        description="Task description",
                        start_time=datetime.datetime(2009,4,18,14),
                        end_time=datetime.datetime(2009,4,18,16),
                        num_volunteers_needed=3,
                        claim_prompt=(
                            "You are about to commit to Tabling on Sat Apr 18th "
                            "from 2:00 p.m. - 4:00 p.m."),
                        claimed_by=[
                            StubObject(first_name="Steven",last_name="Tyler"),
                            StubObject(first_name="Liv",last_name="Tyler")]),
                    Task(
                        id=3,
                        claim_task_url="/chirp/tasks/claim/3.json",
                        task_type=TaskType(
                            short_description="Load In",
                            important_note="May require heavy lifting"),
                        start_time=datetime.datetime(2009,4,19,6),
                        end_time=datetime.datetime(2009,4,19,7),
                        num_volunteers_needed=1,
                        claim_prompt=(
                            "You are about to commit to Load In on Sun Apr 19th "
                            "from 6:00 a.m. - 7:00 a.m."),
                        claimed_by=[]),
                    Task(
                        id=4,
                        claim_task_url="/chirp/tasks/claim/4.json",
                        task_type=TaskType(
                            short_description="Load Out",
                            important_note="May require heavy lifting"),
                        start_time=datetime.datetime(2009,4,19,18),
                        end_time=datetime.datetime(2009,4,19,20),
                        num_volunteers_needed=15,
                        claim_prompt=(
                            "You are about to commit to blah blah"),
                        claimed_by=[])
                ])
        ],
        'title':'Claim A Task'
    })
    return HttpResponse(t.render(c))