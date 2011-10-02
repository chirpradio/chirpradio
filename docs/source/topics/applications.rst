========================
Adding a New Application
========================

Every application has a name that looks like this: "landing_page".
Your code lives in a directory with the same name.
Your templates go under the directory templates/[application name].
Your media files go under the directory media/[application name].

All of your URLs are automatically mapped to be under
http://HOST:PORT/appname/my/url

To make your URLs visible, you need to:

1. Update the top-level urls.py to include your urls.
2. Add your application to INSTALLED_APPS in settings.py.
