#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Tests for b2 infrastructure'''


import os
import uuid
import nose.tools
import pkg_resources

import logging
logger = logging.getLogger(__name__)

from . import b2
from . import restic


TEST_BUCKET_NAME = 'baker-test-' + str(uuid.uuid4())[:8]
SAMPLE_DIR = pkg_resources.resource_filename(__name__, 'data')


def setup():
  '''Sets up the module infrastructure'''
  B2_AUTH_FILE = os.path.expanduser('~/.b2_auth')

  b2_info = b2.get_account_info()

  # 1. checks if we're authorized
  if b2_info is not None:
    logger.info('B2 service is ready - using previous authorization')

  # 2. checks if the user has an auth file hanging around
  elif os.path.exists(B2_AUTH_FILE):
    logger.info("Using b2-auth file at `%s'...", B2_AUTH_FILE)
    with open(B2_AUTH_FILE, 'rt') as f:
      b2_account_id, b2_account_key = \
          [k.strip() for k in f.read().split('\n')]
      b2.authorize_account(b2_account_id, b2_account_key)

  # 3. last resource, auth tokens are set on the environment
  elif 'B2_ACCOUNT_ID' in os.environ and 'B2_ACCOUNT_KEY' in os.environ:
    logger.info("Using b2-auth info at environment...")
    b2.authorize_account(os.environ['B2_ACCOUNT_ID'],
        os.environ['B2_ACCOUNT_KEY'])

  if b2_info is None:
    b2_info = b2.get_account_info()
    assert b2_info

  # reset the enviroment to make sure we're in sync
  os.environ['B2_ACCOUNT_ID'] = b2_info['accountId']
  os.environ['B2_ACCOUNT_KEY'] = b2_info['applicationKey']

  # Creates a test bucket with a given known prefix (and a random bit)
  b2.create_bucket(TEST_BUCKET_NAME)


def teardown():

  b2.remove_bucket(TEST_BUCKET_NAME)


def test_list_buckets():

  output = b2.list_buckets()
  assert TEST_BUCKET_NAME in output


def test_list_bucket_contents():

  # Cleans-up bucket before starting
  b2.empty_bucket(TEST_BUCKET_NAME)

  # Syncs our test directory with the bucket
  b2.sync(TEST_BUCKET_NAME, SAMPLE_DIR)

  output = b2.bucket_contents(TEST_BUCKET_NAME)
  assert 'example.txt' in output


def test_restic_init():

  # Cleans-up bucket before starting
  b2.empty_bucket(TEST_BUCKET_NAME)
  repo = 'b2:%s' % TEST_BUCKET_NAME
  out = restic.init(repo, [], 'password')

  messages = out.split('\n')[:-1] #removes last end-of-line
  nose.tools.eq_(len(messages), 5)
  assert messages[0].startswith('created restic repository')
  assert messages[0].endswith(TEST_BUCKET_NAME)
  assert 'config' in b2.bucket_contents(TEST_BUCKET_NAME)


def test_restic_backup():

  b2.empty_bucket(TEST_BUCKET_NAME)
  repo = 'b2:%s' % TEST_BUCKET_NAME
  restic.init(repo, [], 'password')
  out = restic.backup(SAMPLE_DIR, repo, [], 'hostname', [], 'password')

  messages = out.split('\n')[:-1] #removes last end-of-line
  nose.tools.eq_(len(messages), 7)
  assert messages[0] == ('scan [%s]' % SAMPLE_DIR)
  assert messages[-1].startswith('snapshot')
  assert messages[-1].endswith('saved')


def test_restic_check():

  b2.empty_bucket(TEST_BUCKET_NAME)
  repo = 'b2:%s' % TEST_BUCKET_NAME
  restic.init(repo, [], 'password')
  restic.backup(SAMPLE_DIR, repo, [], 'hostname', [], 'password')
  out = restic.check(repo, [], 'password')

  messages = out.split('\n')[:-1] #removes last end-of-line
  nose.tools.eq_(len(messages), 5)
  nose.tools.eq_(messages[0], 'create exclusive lock for repository')
  nose.tools.eq_(messages[1], 'load indexes')
  nose.tools.eq_(messages[-1], 'no errors were found')


def test_restic_snapshots():

  b2.empty_bucket(TEST_BUCKET_NAME)
  repo = 'b2:%s' % TEST_BUCKET_NAME
  restic.init(repo, [], 'password')
  restic.backup(SAMPLE_DIR, repo, [], 'hostname', [], 'password')
  restic.backup(SAMPLE_DIR, repo, [], 'hostname', [], 'password')
  data = restic.snapshots(repo, ['--json'], 'hostname', 'password')

  # data is a list of dictionaries with the following fields
  #   * time: The time the snapshot was taken (as a datetime.datetime obj)
  #   * tree: The snapshot tree identifier?
  #   * paths: List of paths backed-up on that snapshot
  #   * hostname: The name of the host
  #   * username: The user identifier of the user that made the snapshot
  #   * uid: The user id for the snapshot file
  #   * gid: The groud id for snapshot file
  #   * id: The snapshot identifier
  #   * short_id: A shortened version of ``id``
  nose.tools.eq_(len(data), 2)
  nose.tools.eq_(data[0]['paths'], [SAMPLE_DIR])
  nose.tools.eq_(data[0]['hostname'], 'hostname')
  nose.tools.eq_(data[1]['paths'], [SAMPLE_DIR])
  nose.tools.eq_(data[1]['hostname'], 'hostname')


def test_restic_forget():

  b2.empty_bucket(TEST_BUCKET_NAME)
  repo = 'b2:%s' % TEST_BUCKET_NAME
  restic.init(repo, [], 'password')
  restic.backup(SAMPLE_DIR, repo, [], 'hostname', [], 'password')
  data1 = restic.snapshots(repo, ['--json'], 'hostname', 'password')
  restic.backup(SAMPLE_DIR, repo, [], 'hostname', [], 'password')
  restic.forget(repo, [], 'hostname', True, {'last': 1}, 'password')
  data2 = restic.snapshots(repo, ['--json'], 'hostname', 'password')

  # there are 2 backups which are nearly identical
  nose.tools.eq_(len(data2), 1)
  nose.tools.eq_(data2[0]['parent'], data1[0]['id'])
  assert data2[0]['id'] != data1[0]['id']
