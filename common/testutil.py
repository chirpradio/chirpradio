
"""Common test suite utilities."""

from django import forms as djangoforms

class FormTestCaseHelper(object):
    """Mixin for unittest.TestCase descendants to aid in testing forms."""
    
    def assertNoFormErrors(self, response):
        if response.context is None:
            return
        # if all went well the request probably redirected, 
        # otherwise, there will be form objects with errors:
        forms = []
        for ctx in response.context:
            for cdict in ctx:
                for v in cdict.values():
                    if isinstance(v, djangoforms.BaseForm):
                        forms.append(v)
        for form in forms:
            self.assertEquals(form.errors.as_text(), "")