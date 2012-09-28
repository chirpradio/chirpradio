==========
Installing
==========

.. contents::
      :local:

Using Git
=========

To create a new local repository. Go to
https://github.com/chirpradio/chirpradio
and fork the repository to your own *username* account.
Check out your clone at a URL like this:

.. code-block:: bash

  git clone git@github.com:username/chirpradio.git

You can use your local fork to create topic branches
and make pull requests into the main repo.
Here is a guide on `working with topic branches`_.

.. _`working with topic branches`: https://blog.mozilla.org/webdev/2011/11/21/git-using-topic-branches-and-interactive-rebasing-effectively/


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
