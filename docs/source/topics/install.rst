==========
Installing
==========

.. contents::
      :local:

Using Mercurial
===============

To create a new local repository:

.. code-block:: bash

  hg clone http://chirpradio.googlecode.com/hg/ chirpradio

To pull updates into your local repository:

.. code-block:: bash

  hg pull

To push your changes into the master repository:

.. code-block:: bash

  hg push https://<your username>@chirpradio.googlecode.com/hg/

To get your GoogleCode.com password (needed to push changes):
http://code.google.com/hosting/settings

To push your changes to a temporary location so that other 
developers can review them before they get pushed into the master,
make yourself a clone.  When you're on the main source code page of 
the project, you'll see a link to Clones and under that there is a link 
to create your own clone.  This creates an isolated repository that you 
can safely push your changes to during development.  When your changes 
are ready, someone can easily pull them into the master repository.

For more information about Mercurial, see
`Mercurial: The Definitive Guide <http://hgbook.red-bean.com/>`_, by Bryan O'Sullivan.


Prerequisites
=============

Everything should run in Python 2.5 or greater
http://python.org/download/

Note: Recent Ubuntu Linux versions (at least after Jaunty) ship with Python 2.6.
Many have reported problems running the Google App Engine SDK with a non-2.5.* 
version of Python.  To install Python 2.5 without breaking the default Python
install, you can use this command:

.. code-block:: bash

  sudo apt-get install python2.5

Install the Google App Engine SDK from
http://code.google.com/appengine/downloads.html

If on Mac OS X be sure to start up the launcher once 
so that it prompts you to create symbolic links in /usr/local/google_appengine

Unlike the Google App Engine Python SDK for Mac OS X/Windows, the Linux version 
comes as a zip archive rather than an installer.  To install, just unpack the
archive into /usr/local/google_appengine.  Or you can unpack it to your home directory
and create a symlink in /usr/local/google_appengine.

It's a good idea to install `PyCrypto`_ for pushing code to Google and
so that the SDK works as expected.

On a Debian/Ubuntu system, use this command:

.. code-block:: bash

  sudo apt-get install python-crypto

On Mac OS X you need to grab the `PyCrypto`_ source and run:

.. code-block:: bash

  sudo python setup.py install

To run the JavaScript lint tests (which will fail otherwise) 
you will need the jsl command line tool, aka javascript-lint.

On a Mac OS X system *with* `homebrew`_, type:

.. code-block:: bash

  brew install jsl

(there is probably something similar for Linux)

Running The Development Server
==============================

.. note:: 
  The Google App Engine SDK currently does not run inside a virtualenv.
  This is a known bug.
	
To start up a local server, run

.. code-block:: bash

  python manage.py runserver

Note: If you are running on a system with multiple versions of Python
installed, make sure that you are using the 2.5 version, e.g.:


.. code-block:: bash

  python2.5 manage.py runserver

You can reach your local server by going to http://localhost:8000/
in your web browser.

If you are running this server on a different computer, you need to run
the server with

.. code-block:: bash

  python manage.py runserver 0.0.0.0

instead.  This tells Django to bind to your external IP address and
accept remote connections.

Below, we refer to local URLs like this:  http://HOST:PORT/some/url
You should replace "HOST:PORT" with the appropriate host name/port
combination.

Running The Test Suite
======================

To run all unit tests:

.. code-block:: bash

  python manage.py test

You can also use

.. code-block:: bash

  python manage.py test [application name]

to only run a single application's tests.

.. _`homebrew`: http://mxcl.github.com/homebrew/
.. _`PyCrypto`: http://www.dlitz.net/software/pycrypto/
