#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Tests for baker cmdline tool'''


import os
import time
import nose.tools
import pkg_resources

from .utils import TemporaryDirectory
from .reporter import StdoutCapture, LogCapture

from . import commands
from . import bake


SAMPLE_DIR1 = pkg_resources.resource_filename(__name__, os.path.join('data',
  'dir1'))
SAMPLE_DIR2 = pkg_resources.resource_filename(__name__, os.path.join('data',
  'dir2'))


@nose.tools.raises(SystemExit)
def test_help():

  with StdoutCapture() as buf:
    bake.main(['--help'])


def run_init(repo, b2):

  with TemporaryDirectory() as cache:
    log, sizes, snaps = commands.init({SAMPLE_DIR1: repo}, 'password', cache,
        True, 'hostname', {'condition': 'never'}, b2)

  nose.tools.eq_(len(sizes), 1)
  nose.tools.eq_(len(snaps), 1)
  #assert sizes[0] != 0
  nose.tools.eq_(snaps[0]['paths'], [SAMPLE_DIR1])
  assert 'parent' not in snaps[0] #it is the first snapshot of repository

  messages = log.split('\n')[:-1] #removes last end-of-line

  if b2:
    # skip first couple of messages (using https://api.backblazeb2.com...)
    messages = messages[2:]

  assert messages[0].startswith('created restic repository')
  assert messages[0].endswith(repo)
  nose.tools.eq_(messages[5], 'scan [%s]' % SAMPLE_DIR1)
  assert messages[-1].startswith('snapshot')
  assert messages[-1].endswith('saved')


def test_init_local():

  with TemporaryDirectory() as d:
    run_init(d, {})


def run_init_error(repo, b2):

  with LogCapture('baker') as buf, TemporaryDirectory() as cache:
    configs = {
      SAMPLE_DIR1: repo,
      SAMPLE_DIR2: repo, #error - cannot backup on the same repo
      }
    log, sizes, snaps = commands.init(configs, 'password', cache, False,
        'hostname', {'condition': 'never'}, b2)

  assert 'ERROR during initialization' in buf.read()


def test_init_error():

  with TemporaryDirectory() as d:
    run_init_error(d, {})


def run_init_multiple(repo1, repo2, b2):

  from collections import OrderedDict

  configs = OrderedDict([ #preserves order for tests
    (SAMPLE_DIR1, repo1),
    (SAMPLE_DIR2, repo2),
    ])

  with TemporaryDirectory() as cache:
    log, sizes, snaps = commands.init(configs, 'password', cache, True,
        'hostname', {'condition': 'never'}, b2)

  nose.tools.eq_(len(sizes), 2)
  #assert sizes[0] != 0
  #assert sizes[1] != 0

  nose.tools.eq_(len(snaps), 2)
  nose.tools.eq_(snaps[0]['paths'], [SAMPLE_DIR1])
  assert 'parent' not in snaps[0] #it is the first snapshot of repository
  nose.tools.eq_(snaps[1]['paths'], [SAMPLE_DIR2])
  assert 'parent' not in snaps[1] #it is the first snapshot of repository

  messages = log.split('\n')[:-1] #removes last end-of-line

  messages1 = messages[:int(len(messages)/2)]
  messages2 = messages[int(len(messages)/2):]

  if b2:
    # skip first couple of messages (using https://api.backblazeb2.com...)
    messages1 = messages1[2:]
    messages2 = messages2[2:]

  assert messages1[0].startswith('created restic repository')
  assert messages1[0].endswith(repo1)
  nose.tools.eq_(messages1[5], 'scan [%s]' % SAMPLE_DIR1)
  assert messages1[-1].startswith('snapshot')
  assert messages1[-1].endswith('saved')

  assert messages2[0].startswith('created restic repository')
  assert messages2[0].endswith(repo2)
  nose.tools.eq_(messages2[5], 'scan [%s]' % SAMPLE_DIR2)
  assert messages2[-1].startswith('snapshot')
  assert messages2[-1].endswith('saved')


def test_init_multiple_local():

  with TemporaryDirectory() as d1, TemporaryDirectory() as d2:
    run_init_multiple(d1, d2, {})


def run_init_cmdline(repo, options):

  with StdoutCapture() as buf, TemporaryDirectory() as cache:
    retval = bake.main(options + ['-vvv', 'init', '--overwrite',
      '--cache=%s' % cache, '--hostname=hostname', 'password',
      '%s|%s' % (SAMPLE_DIR1, repo)])

  nose.tools.eq_(retval, 0)
  assert 'Successful initialization of' in buf.read()


def test_init_cmdline():

  with TemporaryDirectory() as d:
    run_init_cmdline(d, [])


def run_update(repo, b2):

  with TemporaryDirectory() as cache:
    log1, sizes1, snaps1 = commands.init({SAMPLE_DIR1: repo}, 'password',
        cache, True, 'hostname', {'condition': 'never'}, b2)
    log2, sizes2, snaps2 = commands.update({SAMPLE_DIR1: repo}, 'password',
        cache, 'hostname', {'condition': 'never'}, b2, {'last': 1},
        period=None, recover=False)

  nose.tools.eq_(len(sizes1), 1)
  #assert sizes1[0] != 0
  nose.tools.eq_(len(snaps1), 1)
  nose.tools.eq_(len(sizes2), 1)
  #assert sizes2[0] != 0
  nose.tools.eq_(len(snaps2), 1)
  assert 'parent' not in snaps1[0]
  assert 'parent' in snaps2[0]
  nose.tools.eq_(snaps2[0]['parent'], snaps1[0]['id'])

  messages = log2.split('\n')[:-1] #removes last end-of-line

  if b2:
    nose.tools.eq_(messages[0], "Using https://api.backblazeb2.com")
    messages = messages[1:]

  assert messages[0].startswith('using parent snapshot')
  nose.tools.eq_(messages[1], 'scan [%s]' % SAMPLE_DIR1)
  assert messages[7].startswith('snapshot')
  assert messages[7].endswith('saved')


def test_update_local():

  with TemporaryDirectory() as d:
    run_update(d, {})


def run_update_recover(repo, b2):

  with TemporaryDirectory() as cache:
    log1, sizes1, snaps1 = commands.init({SAMPLE_DIR1: repo}, 'password',
        cache, True, 'hostname', {'condition': 'never'}, b2)
    log2, sizes2, snaps2 = commands.update({SAMPLE_DIR1: repo}, 'password',
        cache, 'hostname', {'condition': 'never'}, b2, {'last': 1},
        period=None, recover=True)

  nose.tools.eq_(len(sizes1), 1)
  #assert sizes1[0] != 0
  nose.tools.eq_(len(snaps1), 1)
  nose.tools.eq_(len(sizes2), 1)
  #assert sizes2[0] != 0
  nose.tools.eq_(len(snaps2), 1)
  assert 'parent' not in snaps1[0]
  assert 'parent' in snaps2[0]
  nose.tools.eq_(snaps2[0]['parent'], snaps1[0]['id'])

  messages = log2.split('\n')[:-1] #removes last end-of-line

  if b2:
    nose.tools.eq_(messages[0], "Using https://api.backblazeb2.com")
    messages = messages[1:]

  nose.tools.eq_(messages[0], 'successfully removed locks')
  nose.tools.eq_(messages[1], 'counting files in repo')
  assert messages[7].startswith('using parent snapshot')
  nose.tools.eq_(messages[8], 'scan [%s]' % SAMPLE_DIR1)
  assert messages[14].startswith('snapshot')
  assert messages[14].endswith('saved')
  nose.tools.eq_(messages[15], 'counting files in repo')
  nose.tools.eq_(messages[34], 'done')


def test_update_recover():

  with TemporaryDirectory() as d:
    run_update_recover(d, {})


def run_update_multiple(repo1, repo2, b2):

  from collections import OrderedDict

  configs = OrderedDict([ #preserves order for tests
    (SAMPLE_DIR1, repo1),
    (SAMPLE_DIR2, repo2),
    ])

  with TemporaryDirectory() as cache:
    log1, sizes1, snaps1 = commands.init(configs, 'password', cache, True,
        'hostname', {'condition': 'never'}, b2)
    log2, sizes2, snaps2 = commands.update(configs, 'password', cache,
        'hostname', {'condition': 'never'}, b2, {'last': 1}, period=None,
        recover=False)

  nose.tools.eq_(len(sizes1), 2)
  #assert sizes1[0] != 0
  #assert sizes1[1] != 0
  nose.tools.eq_(len(snaps1), 2)
  nose.tools.eq_(len(sizes2), 2)
  #assert sizes2[0] != 0
  #assert sizes2[1] != 0
  nose.tools.eq_(len(snaps2), 2)
  assert 'parent' not in snaps1[0]
  assert 'parent' not in snaps1[1]
  assert 'parent' in snaps2[0]
  assert 'parent' in snaps2[1]
  nose.tools.eq_(snaps2[0]['parent'], snaps1[0]['id'])
  nose.tools.eq_(snaps2[1]['parent'], snaps1[1]['id'])

  messages = log2.split('\n')[:-1] #removes last end-of-line

  messages1 = messages[:int(len(messages)/2)]
  messages2 = messages[int(len(messages)/2):]
  if b2:
    nose.tools.eq_(messages1[0], "Using https://api.backblazeb2.com")
    messages1 = messages1[1:]
  if b2:
    nose.tools.eq_(messages2[0], "Using https://api.backblazeb2.com")
    messages2 = messages2[1:]

  assert messages1[0].startswith('using parent snapshot')
  nose.tools.eq_(messages1[1], 'scan [%s]' % SAMPLE_DIR1)
  assert messages1[7].startswith('snapshot')
  assert messages1[7].endswith('saved')

  assert messages2[0].startswith('using parent snapshot')
  nose.tools.eq_(messages2[1], 'scan [%s]' % SAMPLE_DIR2)
  assert messages2[7].startswith('snapshot')
  assert messages2[7].endswith('saved')


def test_update_local_multiple():

  with TemporaryDirectory() as d1, TemporaryDirectory() as d2:
    run_update_multiple(d1, d2, {})


def run_update_error(repo1, repo2, b2):

  with LogCapture('baker') as buf, TemporaryDirectory() as cache:
    configs = {
      SAMPLE_DIR1: repo1,
      SAMPLE_DIR2: repo2,
      }
    log1, sizes1, snaps1 = commands.init(configs, 'password', cache, True,
        'hostname', {'condition': 'never'}, b2)
    configs = {
      SAMPLE_DIR1: repo1,
      SAMPLE_DIR2: repo2 + '-error', #this directory does not exist
      }
    log2, sizes2, snaps2 = commands.update(configs, 'password', cache,
        'hostname', {'condition': 'never'}, b2, {'last': 1}, period=None,
        recover=False)

  assert 'ERROR during update' in buf.read()


def test_update_error():

  with TemporaryDirectory() as d1, TemporaryDirectory() as d2:
    run_update_error(d1, d2, {})


def run_update_cmdline(repo, options):

  with StdoutCapture() as buf, TemporaryDirectory() as cache:
    retval1 = bake.main(options + ['-vvv', 'init', '--overwrite',
      '--cache=%s' % cache, '--hostname=hostname', 'password',
      '%s|%s' % (SAMPLE_DIR1, repo)])
    retval2 = bake.main(options + ['-vvv', 'update', '--hostname=hostname',
      '--cache=%s' % cache, '--keep=1|0|0|0|0|0', 'password',
      '%s|%s' % (SAMPLE_DIR1, repo)])

  nose.tools.eq_(retval2, 0)
  assert 'Successful update of' in buf.read()


def test_update_cmdline():

  with TemporaryDirectory() as d:
    run_update_cmdline(d, [])


def run_check(repo, b2):

  with TemporaryDirectory() as cache, LogCapture('baker') as buf:
    log1, sizes1, snaps1 = commands.init({SAMPLE_DIR1: repo}, 'password',
        cache, True, 'hostname', {'condition': 'never'}, b2)
    log2, sizes2, snaps2 = commands.check({SAMPLE_DIR1: repo}, 'password',
        cache, 'hostname', {'condition': 'never'}, b2, alarm=1000, period=None)

  nose.tools.eq_(len(sizes1), 1)
  #assert sizes1[0] != 0
  nose.tools.eq_(len(snaps1), 1)
  nose.tools.eq_(len(sizes2), 1)
  #assert sizes2[0] != 0
  nose.tools.eq_(len(snaps2), 1)
  nose.tools.eq_(snaps1, snaps2)

  messages = log2.split('\n')[:-1] #removes last end-of-line

  assert 'check all packs' in messages
  assert 'check snapshots, trees and blobs' in messages
  nose.tools.eq_(messages[-1], 'no errors were found')

  assert 'Successful check of 1 repository' in buf.read()


def test_check_local():

  with TemporaryDirectory() as d:
    run_check(d, {})


def run_check_alarm(repo, b2):

  with TemporaryDirectory() as cache, LogCapture('baker') as buf:
    log1, sizes1, snaps1 = commands.init({SAMPLE_DIR1: repo}, 'password',
        cache, True, 'hostname', {'condition': 'never'}, b2)
    time.sleep(1.1) #reach alarm condition
    log2, sizes2, snaps2 = commands.check({SAMPLE_DIR1: repo}, 'password',
        cache, 'hostname', {'condition': 'never'}, b2, alarm=1, period=None)

  nose.tools.eq_(len(sizes1), 1)
  #assert sizes1[0] != 0
  nose.tools.eq_(len(snaps1), 1)
  nose.tools.eq_(len(sizes2), 1)
  #assert sizes2[0] != 0
  nose.tools.eq_(len(snaps2), 1)
  nose.tools.eq_(snaps1, snaps2)

  messages = log2.split('\n')[:-1] #removes last end-of-line

  assert 'check all packs' in messages
  assert 'check snapshots, trees and blobs' in messages
  nose.tools.eq_(messages[-1], 'no errors were found')

  assert 'ALARM condition (1 second) reached' in buf.read()


def test_check_alarm_local():

  with TemporaryDirectory() as d:
    run_check_alarm(d, {})


def run_check_multiple(repo1, repo2, b2):

  from collections import OrderedDict

  configs = OrderedDict([ #preserves order for tests
    (SAMPLE_DIR1, repo1),
    (SAMPLE_DIR2, repo2),
    ])

  with TemporaryDirectory() as cache, LogCapture('baker') as buf:
    log1, sizes1, snaps1 = commands.init(configs, 'password', cache, True,
        'hostname', {'condition': 'never'}, b2)
    time.sleep(1.1)
    log2, sizes2, snaps2 = commands.check(configs, 'password', cache,
        'hostname', {'condition': 'never'}, b2, alarm=1, period=None)

  nose.tools.eq_(len(sizes1), 2)
  #assert sizes1[0] != 0
  #assert sizes1[1] != 0
  nose.tools.eq_(len(snaps1), 2)
  nose.tools.eq_(len(sizes2), 2)
  #assert sizes2[0] != 0
  #assert sizes2[1] != 0
  nose.tools.eq_(len(snaps2), 2)
  nose.tools.eq_(snaps1, snaps2)

  messages = log2.split('\n')[:-1] #removes last end-of-line

  messages1 = messages[:int(len(messages)/2)]
  messages2 = messages[int(len(messages)/2):]
  if b2:
    nose.tools.eq_(messages1[0], "Using https://api.backblazeb2.com")
    messages1 = messages1[1:]
  if b2:
    nose.tools.eq_(messages2[0], "Using https://api.backblazeb2.com")
    messages2 = messages2[1:]

  assert 'check all packs' in messages1
  assert 'check snapshots, trees and blobs' in messages1
  nose.tools.eq_(messages1[-1], 'no errors were found')

  assert 'check all packs' in messages2
  assert 'check snapshots, trees and blobs' in messages2
  nose.tools.eq_(messages2[-1], 'no errors were found')

  assert 'ALARM condition (1 second) reached' in buf.read()


def test_check_local_multiple():

  with TemporaryDirectory() as d1, TemporaryDirectory() as d2:
    run_check_multiple(d1, d2, {})


def run_check_error(repo1, repo2, b2):

  with LogCapture('baker') as buf, TemporaryDirectory() as cache:
    configs = {
      SAMPLE_DIR1: repo1,
      SAMPLE_DIR2: repo2,
      }
    log1, sizes1, snaps1 = commands.init(configs, 'password', cache, True,
        'hostname', {'condition': 'never'}, b2)
    configs = {
      SAMPLE_DIR1: repo1,
      SAMPLE_DIR2: repo2 + '-error', #this directory does not exist
      }
    log2, sizes2, snaps2 = commands.check(configs, 'password', cache,
        'hostname', {'condition': 'never'}, b2, alarm=0, period=None)

  assert 'ERROR during check' in buf.read()


def test_check_error():

  with TemporaryDirectory() as d1, TemporaryDirectory() as d2:
    run_check_error(d1, d2, {})


def run_check_cmdline(repo, options):

  with StdoutCapture() as buf, TemporaryDirectory() as cache:
    retval1 = bake.main(options + ['-vvv', 'init', '--overwrite',
      '--cache=%s' % cache, '--hostname=hostname', 'password',
      '%s|%s' % (SAMPLE_DIR1, repo)])
    retval2 = bake.main(options + ['-vvv', 'check', '--hostname=hostname',
      '--cache=%s' % cache, '--alarm=1000', 'password',
      '%s|%s' % (SAMPLE_DIR1, repo)])

  nose.tools.eq_(retval2, 0)
  assert 'Successful check of' in buf.read()


def test_check_cmdline():

  with TemporaryDirectory() as d:
    run_check_cmdline(d, [])
