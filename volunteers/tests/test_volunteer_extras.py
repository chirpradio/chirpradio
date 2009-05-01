
import unittest
from chirp.volunteers.tests.base import eq_
from django.template import loader
from django.template import Context

__all__ = ['TestIfGreaterThan']

class TestIfGreaterThan(unittest.TestCase):
    
    def test_literal_false(self):
        tmpl = loader.get_template_from_string("""
        {% load volunteers_extras %}
        {% ifgreaterthan 1 2 %}
        yes
        {% endifgreaterthan %}
        """)
        val = tmpl.render(Context({})).strip()
        eq_(val, "")
    
    def test_literal_positive(self):
        tmpl = loader.get_template_from_string("""
        {% load volunteers_extras %}
        {% ifgreaterthan 2 1 %}
        yes
        {% endifgreaterthan %}
        """)
        val = tmpl.render(Context({})).strip()
        eq_(val, "yes")
    
    def test_variable_false(self):
        tmpl = loader.get_template_from_string("""
        {% load volunteers_extras %}
        {% ifgreaterthan foo bar %}
        yes
        {% endifgreaterthan %}
        """)
        val = tmpl.render(Context({'foo': 1, 'bar': 2})).strip()
        eq_(val, "")
    
    def test_variable_positive(self):
        tmpl = loader.get_template_from_string("""
        {% load volunteers_extras %}
        {% ifgreaterthan foo bar %}
        yes
        {% endifgreaterthan %}
        """)
        val = tmpl.render(Context({'foo': 2, 'bar': 1})).strip()
        eq_(val, "yes")
        