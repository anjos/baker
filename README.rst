.. image:: https://travis-ci.org/anjos/baker.svg?branch=master
   :target: https://travis-ci.org/anjos/baker
.. image:: https://img.shields.io/docker/pulls/anjos/baker.svg
   :target: https://hub.docker.com/r/anjos/baker/

-------
 Baker
-------

A bunch of utilities to backup my QNAS folders on BackBlace B2 Buckets. It
provides ways to upload, list, delete and retrieve files from the service.


Installation
------------

I advise you to install a Conda_-based environment for deployment with this
command line::

  $ conda create --override-channels -c anjos -c defaults -n baker python=x.y baker

Where ``x.y`` can be either ``2.7`` or ``3.6``. Once the environment is
installed, activate it to be able to call binaries::

  $ source activate baker


Usage
-----

There is a single program that you can launch as a daemon on your system::

  $ ./bin/bake --help

And a complete help message will be displayed.


Development
-----------

I advise you to install a Conda_-based environment for development with this
command line::

  $ conda env create -f dev.yml


Build
=====

To build the project and make it ready to run, do::

  $ source activate baker-dev
  $ buildout

This command should leave you with a functional environment.


Testing
=======

To test the package, run the following::

  $ ./bin/nosetests -sv --with-coverage --cover-package=baker


Conda Builds
============

Building dependencies requires you install ``conda-build``. Do the following to
prepare::

  $ conda install -n root conda-build anaconda-client

Then, you can build dependencies one by one, in order::

  $ vi ./scripts/conda-build-all.sh #comment/uncomment what to compile
  $ ./scripts/conda-build-all.sh

.. note::

   The process above requires the file ``${HOME}/.b2_auth`` exists and
   contains, both the user account id and key for BackBlaze's B2. Container
   based building of Conda_ packages will not work otherwise.


Anaconda Uploads
================

To upload all built dependencies (so you don't have to re-build them
everytime), do::

  $ anaconda login
  # enter credentials
  $ anaconda upload <conda-bld>/*-64/restic-*.tar.bz2
  $ anaconda upload <conda-bld>/*-64/{yapf,logfury,b2,schedule}-*.tar.bz2


Docker Image Building
=====================

To build a readily deployable docker image, do::

  $ docker build --rm -t anjos/baker:latest -t anjos/baker:vx.y.z --build-arg VERSION=x.y.z .
  $ #upload it like this:
  $ docker push anjos/baker:latest
  $ docker push anjos/baker:vx.y.z


.. note::

   Before running the above command, make sure to tag this package
   appropriately and to build and deploy conda packages for such a release.
   Also build the equivalent version-named container using ``-t
   anjos/baker:vX.Y.Z``.


Deployment
----------

QNAP has a proprietary packaging format for native applications called QPKG_.
While it allows one to create apps that are directly installable using QNAP's
App Center, it also ties in the running environment (mostly libc's
dependencies) for the current OS. This implies applications need to be
re-packaged at every major OS release. It may also bring conflicts with Conda's
default channel ABIs.

Instead of doing so, I opted for a deployment based on Docker containers. The
main advantages of this approach is that containers are (almost) OS independent
and there is a huge source of information and resources for building container
images on the internet.

To deploy baker, just download the released image at DockerHub_ and create a
container through Container Station. The container starts the built-in ``bake``
application that backups your folders based on command-line options and
arguments. I typically mount the directories to be backed up with suggestive
names (set this in "Advanced Settings" -> "Shared folders") and in
**read-only** mode. I run the ``init`` command once to initialize the restic
repository::

  # mount data to backup at container's "/data-to-backup", read-only mode
  -vv init --b2-account-id=yourid --b2-account-key=yourkey --hostname=my-host "password" "/data-to-backup|b2:data-bucket-for-restic"

If you'd like to use Gmail for sending e-mails about latest activity, just make
sure to set the ``--email`` flag and set your username and specific-app
password (to avoid 2-factor authentication). ``baker`` should handle this
flawlessly. Other e-mail providers should also be reacheable in the same way.

Once the initialization of the repository is done, you may proceed and create a
second container that will run in daemon mode, updating the repository
constantly, once a day. Container settings should be the same as for the
initialization. The command-line should be slightly different::

  # mount data to backup at container's "/data-to-backup", read-only mode
  -vv update --b2-account-id=yourid --b2-account-key=yourkey --hostname=my-host "password" "/data-to-backup|b2:data-bucket-for-restic"

Optionally, implement monitoring in a third, separate container, that will
execute the following command (alerts you if latest snapshots are older than a
certain threshold - in seconds)::

  # mount data to backup at container's "/data-to-backup", read-only mode
  -vv check --alarm=172800 --b2-account-id=yourid --b2-account-key=yourkey --hostname=my-host "password" "/data-to-backup|b2:data-bucket-for-restic"


.. Place your references after this line
.. _conda: http://conda.pydata.org/miniconda.html
.. _mediainfo: https://mediaarea.net/en/MediaInfo
.. _qpkg: https://wiki.qnap.com/wiki/QPKG_Development_Guidelines
.. _dockerhub: https://hub.docker.com/r/anjos/baker/
