============
Deployment
============

To deploy a new version of the application to https://chirpradio.appspot.com/ , follow these steps:

Create a tag with today's date like::

    git tag release-v1-YYYY-MM-DD-1

Push all your changes, including the new tag::

    git push && git push --tags

Make sure you have the `Google Cloud SDK`_ installed and type this command from the root directory to deploy::

    gcloud app deploy --version 1 --project chirpradio-hrd

.. _`Google Cloud SDK`: https://cloud.google.com/sdk/

You can monitor the application at https://console.cloud.google.com/appengine?project=chirpradio-hrd
