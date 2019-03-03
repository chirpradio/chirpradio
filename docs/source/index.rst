============================
CHIRP Radio Developer Guide
============================

`CHIRP`_ is a non-profit organization that runs a community `radio station
<http://chirpradio.org/>`_ in Chicago focused on new music and the arts. This
is the source code for some internal applications we are building.

* Listen to `CHIRP Radio`_ here
* Keep up with the `CHIRP organization`_ here

These are internal tools used in the daily operation of our station. In
particular, this is not meant to be a turnkey system for running a radio
station. Many things about this code are CHIRP-specific. However, all code is
open source and we may be able to provide guidance to anyone wishing to
generalize the apps and modules for other uses, `just ask
<http://groups.google.com/group/chirpdev>`_.

We use `Google App Engine`_ and `Django`_ as the platform for these
applications.

.. _`CHIRP Radio DJ applications`: http://code.google.com/p/chirpradio/
.. _`CHIRP`: http://chicagoindieradio.org/
.. _`CHIRP Radio`: http://chirpradio.org/
.. _`CHIRP Organization`: http://chicagoindieradio.org/
.. _`Google App Engine`: http://code.google.com/appengine/
.. _`Django`: https://www.djangoproject.com/

Documentation
=============

Here's how to get started developing `CHIRP Radio DJ applications`_.

.. toctree::
   :maxdepth: 1
   :glob:

   topics/install
   topics/bootstrapping
   topics/test-instance
   topics/users-and-auth
   topics/applications
   topics/style-guide
   topics/deployment

The CHIRP API
=============

There is a `hosted API <http://code.google.com/p/chirpradio/wiki/TheChirpApi>`_
to get CHIRP data for mobile apps.

Community
=========

Feel free to connect and ask questions on the
`CHIRP Dev <http://groups.google.com/group/chirpdev>`_ mailing list.

Other code
==========

Looking for something else by CHIRP?

* The `CHIRP iPhone app <http://itunes.apple.com/us/app/chirp-radio/id373395037?mt=8>`_
* The `CHIRP Android app <https://github.com/chirpradio/chirpradio-android/>`_
* `The CHIRP Radio Machine <https://github.com/chirpradio/chirpradio-machine>`_: music library / broadcast stream

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
