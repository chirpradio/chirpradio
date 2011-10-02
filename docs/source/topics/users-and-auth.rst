========================
Users and Authentication
========================

The chirpradio applications use custom middleware to enforce access
controls.  It will automatically take care of details like blocking
inactive users or redirecting unauthenticated users to the login page.

Roles
=====

Roles are a light-weight substitute for the standard Django auth module's
notion of groups.

The list of valid roles is hard-wired into auth/roles.py, so adding a
new role requires an updated version of the app to be pushed into
production.

Access Policy
=============

With only a very few exceptions, all of the URLs that are part of the
chirpradio applications are only accessible to signed-in users.  If an
unauthenticated user tries to visit such a URL, they will be
redirected to a login page, and then redirected back to the
originally-requested page after they have successfully signed in.
This behavior is controlled by custom middleware defined in
auth/middleware.py.

Access can be further restricted based on role using the decorators
defined in auth/decorators.py.  For example, this is how to define a
view that is only accessible to a user who has the role "volunteer
coordinator"::

    from auth import roles
    from auth.decorators import require_role

    @require_role(roles.VOLUNTEER_COORDINATOR)
    def my_view(request):
        ... etc ...

User Information
================

Our User object is defined in auth/models.py.  It is similar, but not
identical, to the stock Django User object.

For any incoming HttpRequest, the user attribute is automatically populated
with the logged-in user's User object.

.. code-block:: python

    def my_hello_world_view(request):
        return HttpResponse('Hello %s!' % request.user)

Users are keyed on their email addresses:
    some_user = User.get_by_email(email_addr)

However, users are allowed to change their email address.
Applications should not put them in the datastore or otherwise assume
that they are invariant.

Unit Testing
============

To simplify unit testing, the CHIRP authentication system is
integrated with Django's django.test.client module.  You can use the
login method to test against fake users with various characteristics.

.. code-block:: python

    from django.test.client import Client

    my_client = Client()
    # You can set any of the User object's attributes here.
    my_client.login(email="test@test.com", roles=[role1, role2])
    response = my_client.get("/some/page/to/test")

For more information on unit testing in Django, please see
http://docs.djangoproject.com/en/1.0/topics/testing/
