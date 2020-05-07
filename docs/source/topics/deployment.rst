============
Deployment
============

To deploy a new version of the application to https://chirpradio.appspot.com/ , follow these steps:

Create a tag with today's date like::

    git tag release-v1-YYYY-MM-DD-1

Push all your changes, including the new tag::

    git push && git push --tags

Make sure you have the `Google Cloud SDK`_ installed and type this command from the root directory to deploy::

    gcloud app deploy --no-promote --no-stop-previous-version --project=chirpradio-hrd --version=VERSION_NAME

The new version can be tested on a version-specific URL that will be listed in the console output of that command as the "target url".

Traffic can be split between the previous and new version and gradually migrated over for further testing and control: https://cloud.google.com/appengine/docs/standard/python/splitting-traffic

.. _`Google Cloud SDK`: https://cloud.google.com/sdk/

You can monitor the application at https://console.cloud.google.com/appengine?project=chirpradio-hrd
