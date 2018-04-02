#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Tests for baker cmdline tool'''


import os
import logging
import nose.tools
import pkg_resources

from .utils import TemporaryDirectory
from .reporter import LogCapture


SAMPLE_DIR1 = pkg_resources.resource_filename(__name__, os.path.join('data',
  'dir1'))
SAMPLE_DIR2 = pkg_resources.resource_filename(__name__, os.path.join('data',
  'dir2'))


@nose.tools.raises(SystemExit)
def test_help():

  from .bake import main
  main(['--help'])


def test_init_local():

  from .bake import init

  with TemporaryDirectory() as d:
    log, sizes, snaps = init({SAMPLE_DIR1: d}, 'password', True, 'hostname',
      {}, {})

  nose.tools.eq_(len(sizes), 1)
  nose.tools.eq_(len(snaps), 1)
  assert sizes[0] != 0
  nose.tools.eq_(snaps[0]['paths'], [SAMPLE_DIR1])
  assert 'parent' not in snaps[0] #it is the first snapshot of repository

  messages = log.split('\n')[:-1] #removes last end-of-line

  assert messages[0].startswith('created restic repository')
  assert messages[0].endswith(d)
  nose.tools.eq_(messages[5], 'scan [%s]' % SAMPLE_DIR1)
  assert messages[-1].startswith('snapshot')
  assert messages[-1].endswith('saved')


def test_init_multiple_local():

  from .bake import init

  with TemporaryDirectory() as d1, TemporaryDirectory() as d2:
    configs = {
      SAMPLE_DIR1: d1,
      SAMPLE_DIR2: d2,
      }
    log, sizes, snaps = init(configs, 'password', True, 'hostname', {}, {})

  nose.tools.eq_(len(sizes), 2)
  assert sizes[0] != 0
  assert sizes[1] != 0

  nose.tools.eq_(len(snaps), 2)
  nose.tools.eq_(snaps[0]['paths'], [SAMPLE_DIR1])
  assert 'parent' not in snaps[0] #it is the first snapshot of repository
  nose.tools.eq_(snaps[1]['paths'], [SAMPLE_DIR2])
  assert 'parent' not in snaps[1] #it is the first snapshot of repository

  messages = log.split('\n')[:-1] #removes last end-of-line

  messages1 = messages[:int(len(messages)/2)]
  messages2 = messages[int(len(messages)/2):]

  assert messages1[0].startswith('created restic repository')
  assert messages1[0].endswith(d)
  nose.tools.eq_(messages1[5], 'scan [%s]' % SAMPLE_DIR1)
  assert messages1[-1].startswith('snapshot')
  assert messages1[-1].endswith('saved')

  assert messages2[0].startswith('created restic repository')
  assert messages2[0].endswith(d)
  nose.tools.eq_(messages2[5], 'scan [%s]' % SAMPLE_DIR2)
  assert messages2[-1].startswith('snapshot')
  assert messages2[-1].endswith('saved')



def test_update_local():

  from .bake import init, update

  with TemporaryDirectory() as d:
    log1, sizes1, snaps1 = init({SAMPLE_DIR1: d}, 'password', True, 'hostname',
        {}, {})
    log2, sizes2, snaps2 = update({SAMPLE_DIR1: d}, 'password', 'hostname', {},
        {}, {'last': 1}, period=None)

  nose.tools.eq_(len(sizes1), 1)
  assert sizes1[0] != 0
  nose.tools.eq_(len(snaps1), 1)
  nose.tools.eq_(len(sizes2), 1)
  assert sizes2[0] != 0
  nose.tools.eq_(len(snaps2), 1)
  assert 'parent' not in snaps1[0]
  assert 'parent' in snaps2[0]
  nose.tools.eq_(snaps2[0]['parent'], snaps1[0]['id'])

  messages = log2.split('\n')[:-1] #removes last end-of-line

  assert messages[0].startswith('using parent snapshot')
  nose.tools.eq_(messages[1], 'scan [%s]' % SAMPLE_DIR1)
  assert messages[7].startswith('snapshot')
  assert messages[7].endswith('saved')
