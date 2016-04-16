======================================
Creating a Test Instance on App Engine
======================================

#. Go to the `App Engine console <http://appspot.com>`_ and, from the top menu, select "Create project".
#. Name the project chirpradio-test and hit Create.
#. Note the project ID. It will be something like chirpradio-test-123.
#. Go to the directory where you cloned `chirpradio/chirpradio <https://github.com/chirpradio/chirpradio>`_.
#. To upload the code to the new project, run this at the command line::

     appcfg.py -A <your project id> update .

#. Go to :code:`http://<your project id>.appspot.com` and verify that the site is up.
#. Go to the `API Manager credentials <https://console.cloud.google.com/apis/credentials>`_ page.
#. Select Create credentials > Service account key.
#. Select App Engine default service account, choose JSON, and hit Create. The newly-generated key will be automatically downloaded to your computer.
#. Connect to your remote datastore using the `Remote API Shell <https://cloud.google.com/appengine/docs/python/tools/remoteapi#using_the_remote_api_shell>`_::

     GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account_key.json remote_api_shell.py -s <your project id>.appspot.com

#. To create a new user, run the following code in the shell:

   .. code-block:: python

    from auth.models import User
    user = User(email='first.last@email.com', first_name='First', last_name='Last', is_superuser=True)
    user.set_password('password')
    user.save()

#. Go ahead and login using the email and password you set for your user in the Remote API Shell.
