import logging
import traceback

from django.utils import simplejson
from django.http import HttpResponse


def respond_with_json(func):
    """Convert a handler's return value into a JSON-ified HttpResponse."""
    def wrapper(*args, **kwargs):
        try:
            response_py = func(*args, **kwargs)
            status = 200
        except Exception, err:
            logging.exception('Error in JSON response')
            response_py = {
                'success': False,
                'error': repr(err),
                'traceback': traceback.format_exc()
                }
            status = 500
        return HttpResponse(simplejson.dumps(response_py), 
                            mimetype='application/json', 
                            status=status )
    return wrapper
