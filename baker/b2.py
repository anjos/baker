#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Utilities to handle BackBlaze B2 via command-line'''

import os
import json
import copy

import logging
logger = logging.getLogger(__name__)

from .utils import run_cmdline, which, TemporaryDirectory


B2_BIN = which('b2')
logger.info('Using b2 from `%s\'', B2_BIN)


def run_b2(args):
  '''Runs the b2 binary with the provided arguments


  Parameters:

    args (list): List of arguments to pass to the ``b2`` binary


  Returns:

    str: Standard output and error

  '''

  assert B2_BIN, "The executable `b2' must be available on your ${PATH}"
  return run_cmdline([B2_BIN] + args)


def get_account_info():
  '''Returns the current account information

  This function will return a dictionary with account information retrieved
  from the SQLite file kept by the b2 command-line program. It will return
  and empty dictionary if no authorization information is available.


  Returns:

    dict: The account information, if the user is logged-in

  '''

  try:
    return json.loads(run_b2(['get-account-info']))
  except RuntimeError as e:
    return None


def clear_account():
  '''Logs off, removes the authorization file kept locally and all credentials
  '''

  return run_b2(['clear-account'])


def authorize_account(account_id, key):
  '''Runs the authorization procedure for the b2 cmdline tool


  Parameters:

    account_id (str): The BackBlaze B2 account identifier

    key (str): The BackBlaze B2 key to use to run the command. This key must
      have access to the specified bucket.

  '''

  return run_b2(['authorize-account', account_id, key])


def sync(bucket, path):
  '''Synchronizes contents of the given path to the bucket

  This function is primarily for tests as it **destructively** syncs local
  folder contents to the remote bucket


  Parameters:

    bucket (str): The name of the bucket to use for sync'ing
    path (str): Local path to a directory whose contents will be synchronized
      with the bucket

  '''

  return run_b2(['sync', '--allowEmptySource', '--delete', path,
    'b2://%s' % bucket])


def empty_bucket(name):
  '''Empties the contents of a BackBlaze B2 bucket

  Follows the following implementation advice: https://help.backblaze.com/hc/en-us/articles/225556127-How-Can-I-Easily-Delete-All-Files-in-a-Bucket-


  Parameters:

    name (str): The name of the bucket to remove contents from


  '''

  with TemporaryDirectory() as d:
    return sync(name, d) #remove all contents


def remove_bucket(name):
  '''Removes a BackBlaze B2 bucket

  Follows the following implementation advice: https://help.backblaze.com/hc/en-us/articles/225556127-How-Can-I-Easily-Delete-All-Files-in-a-Bucket-


  Parameters:

    name (str): The name of the bucket to remove


  Returns:

    dict: With the JSON contents returned by the ``delete-bucket`` command. The
    snippet contains the deleted bucket information.

  '''

  empty_bucket(name)
  return json.loads(run_b2(['delete-bucket', name]))


def create_bucket(name, tp='allPrivate'):
  '''Creates a new (private) bucket


  Parameters:

    name (str): The name of the bucket to remove
    tp (str, Optional): Either ``allPrivate`` or ``allPublic``

  '''

  return run_b2(['create-bucket', name, tp])


def list_buckets():
  '''List all available buckets


  Returns:

    dict: A dictionary of buckets available in which keys are bucket names and
    values are bucket properties. Each value contains two bucket properties:
    ID (hexadecimal string) and bucket type (either "allPublic" or
    "allPrivate").

  '''

  out = run_b2(['list-buckets'])
  if out.endswith('\n'): out = out[:-1]
  objects = out.split('\n')
  objects = [k.split() for k in objects]
  return dict([(k[-1], k[:-1]) for k in objects])


def bucket_contents(name, folder=None):
  '''List bucket contents


  Parameters:

    name (str): The name of the bucket to check
    path (str, Optional): Sub-folder within the bucket to check for contents


  Returns:

    list: A list containing the files on the given bucket and subfolder (if
    provided)

  '''

  args = ['ls', name]
  if folder: cmd += [folder]
  out = run_b2(args)
  if out.endswith('\n'): out = out[:-1]
  return out.split('\n')
