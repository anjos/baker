.. image:: https://travis-ci.org/anjos/backuper.svg?branch=master
   :target: https://travis-ci.org/anjos/backuper

----------------------------------------------------------------------
 The Backuper - Utilities for Backing-Up my QNAS folders on BackBlaze
----------------------------------------------------------------------

A bunch of utilities to backup my QNAS folders on BackBlace B2 Buckets. It
provides ways to upload, list, delete and retrieve files from the service.


Install
=======

Use the Conda_ package to install the backuper and all of its dependencies::

  $ conda create --override-channels -c anjos -c defaults -n backuper python=3.6 backuper
  $ source activate backuper


API Keys and Passwords
----------------------

For some of the functionality, you'll need to setup API keys that will be used
to contact BackBlaze. You may pass the keys everytime you use one of the
applications bundled or permanently set it up on your account and let the apps
find it. The search order is the following:

1. If a file named ``.backuperrc`` exists on the current directory, then it is
   loaded and it should contain a variable named ``tmdb`` (or ``tvdb``) inside
   a section named ``apikeys``, with the value of your API key
2. If a file named ``.backuperrc`` exists on your home directory and none exist
   on your current directory, than that one is use instead.
3. If none of the above exist and you don't pass an API key via command-line
   parameters, then an error is produced and the application will stop.

The syntax of the ``.backuperrc`` file is simple, following a Windows
INI-style syntax::

  [apikeys]
  amazon = 1234567890abcdef123456

  [passwords]
  Name1 = abcdef
  Name2 = 123456


Usage
=====

There are various utilities you may use for backing-up, listing and erasing
content from the Amazon service.


Backing-up
----------

To backup, select one or multiple local source directories and an Amazon
Glacier volume. The contents of the local source directories will be backed-up
on the remote server. An encryption pass


Listing
-------

You can list the file contents of a given volume like this:



Deleting
--------

To delete all contents of a volume and remove it, execute the following
command:




Development
===========

Here are instructions if you wish to change any part of this library.


Build
-----

To build the project and make it ready to run, do::

  $ conda env create --force -f dev.yml
  $ source activate backuper-dev
  $ buildout

This command should leave you with a functional development environment.


Testing
-------

To test the package, run the following::

  $ ./bin/nosetests -sv --with-coverage --cover-package=backuper


Conda Builds
============

Building dependencies requires you install ``conda-build``. Do the following to
prepare::

  $ conda install -n root conda-build anaconda-client

Then, you can build dependencies one by one, in order::

  $ for p in deps/rsa deps/s3transfer deps/botocore deps/awscli deps/ipdb deps/zc.buildout; do conda build $p; done

Anaconda Uploads
================

To upload all built dependencies (so you don't have to re-build them
everytime), do::

  $ anaconda login
  # enter credentials
  $ anaconda upload <conda-bld>/noarch/{rsa,s3transfer,botocore,awscli,ipdb,zc.buildout}-*.tar.bz2


.. Place your references after this line
.. _conda: http://conda.pydata.org/miniconda.html
