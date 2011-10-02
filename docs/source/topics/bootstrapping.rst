===================================
Bootstrapping Your Dev Setup
===================================

To do anything interesting with your development site you'll need some test
data and other bits of scaffolding.

Creating a New Local Test User
==============================

If you are running locally, you can create a test account by:

1. Go to http://HOST:PORT/_ah/login
2. Enter the email address that you want to use for testing, and check
   the "sign in as administrator" box.  Then click the "login" button.
3. Go to http://HOST:PORT/auth/_bootstrap.  Hitting this URL will
   create a new user account and then immediately redirect you to a
   login page.
4. Now log in using the email address that you chose in step 2 and the
   password "test".

The test user created by this method has superuser privileges, so you
should be able to add other test accounts by visiting
http://HOST:PORT/auth/

Resetting a Local Test User's Password
======================================

Since a local development instance cannot send email, the normal
password recovery mechanism cannot be used for test accounts.  If you
forget a test account's password, you can

1. Go to http://HOST:PORT/_ah/admin/datastore?kind=User
2. Find the user whose password you wish to reset, then click on the
   "Key" hyperlink in order to edit it.
3. Replace the entity's password attribute with the following:
   32e6e8b1d913ca40bd3f1d683ba65925bba1f559381f
4. Click the "Save Changes" button.

You should now be able to log in as that user with the password "test".

Working With Artists and Albums
===============================

To see some artists and albums in the DJ Database, open this special
URL: http://127.0.0.1:8000/djdb/_bootstrap

This adds David Bowie, The Clash, and a few others.

Working With the Datastore Config
=================================

Open http://127.0.0.1:8000/common/_init_config to initialize the Datastore
config object.
