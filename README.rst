CHIRP Radio is a non-profit organization that runs a community radio station in Chicago
focused on new music and the arts.

Get started by reading the `development guide`_.

.. _`development guide`: http://chirpradio.readthedocs.org/en/latest/index.html

This is the code for CHIRP's internal web applications.  The apps run
on Google App Engine, under the 'chirpradio' project.  The source code is
hosted on Google Code, also under the 'chirpradio' project.

For the chirpradio developer dashboard, go to:
http://appengine.google.com/dashboard?&app_id=chirpradio-hrd

For the end-user landing page, go to:
http://chirpradio.appspot.com/

For the Google Code project:
http://code.google.com/p/chirpradio

Helpful external documentation:

* App Engine Python API
  https://cloud.google.com/appengine/docs/python/?csw=1


Documentation
=============

To read or work on the developer documentation locally,
create a `virtualenv`_, and install the requirements::

    pip install -r docs/requirements.txt

Run this to build the docs::

    make -C docs/ html

Open ``docs/build/html/index.html`` in a web browser.

.. _virtualenv: https://virtualenv.pypa.io/en/latest/


Third party code
================

* google-app-engine-django

Some of the files in this directory and all of files under the
``appengine_django/`` subdirectory are based on rev 81 of the
``google-app-engine-django`` Subversion repository.

* Django

All files in django.zip are taken from Django 1.0.2-final.  It was
constructed by running the following commands::

  zip -r django.zip django/__init__.py django/bin django/core \
                    django/db django/dispatch django/forms \
                    django/http django/middleware django/shortcuts \
                    django/template django/templatetags \
                    django/test django/utils django/views

  zip -r django.zip django/conf -x 'django/conf/locale/*'

These commands were taken from
http://code.google.com/appengine/articles/django10_zipimport.html

Some of the CSS files media/common/css are based on files that
were copied from django/contrib/admin/media/css.
