#!/usr/bin/env python


'''An interface to the restic command-line application'''


import os
import time
import copy
import subprocess

import logging
logger = logging.getLogger(__name__)


def _which(env, program):
  '''Pythonic version of the `which` command-line application'''

  def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

  fpath, fname = os.path.split(program)
  if fpath:
    if is_exe(program): return program
  else:
    for path in os.environ["PATH"].split(os.pathsep):
      exe_file = os.path.join(path, program)
      if is_exe(exe_file): return exe_file

  return None


RESTIC_BIN = _which('restic')
logger.info('Using restic from `%s\'', RESTIC_BIN)


def _human_time(seconds, granularity=2):
  '''Returns a human readable time string like "1 day, 2 hours"'''

  result = []

  for name, count in intervals:
    value = seconds // count
    if value:
      seconds -= value * count
      if value == 1:
        name = name.rstrip('s')
      result.append("{} {}".format(value, name))
    else:
      # Add a blank if we're in the middle of other values
      if len(result) > 0:
        result.append(None)

  return ', '.join([x for x in result[:granularity] if x is not None])


def run_restic(global_options, subcmd, subcmd_options, password,
    b2_account_id=None, b2_account_key=None):
  '''Runs restic on a contained environment, report output and status


  Runs the restic binary on the provided environment, capturing output and
  status exit code.


  Parameters:

    global_options (list): A list of global options to pass to restic

    subcmd (str): The subcommand to call

    subcmd_options (list): A list of subcommand specific options

    password (str): The restic repository password

    b2_account_id (str, Optional): The BackBlaze B2 account identifier. If set,
      then setup B2_ACCOUNT_ID environment variable before calling restic.

    b2_account_id (str, Optional): The BackBlaze B2 account key. If set,
      then setup B2_ACCOUNT_KEY environment variable before calling restic.


  Returns:

    bool: ``True`` if the program returned 0 exit status (ran w/o problems)

  '''

  env = copy.copy(os.environ)
  env.setdefault('RESTIC_PASSWORD', password)
  if b2_account_id: env.setdefault('B2_ACCOUNT_ID', b2_account_id)
  if b2_account_key: env.setdefault('B2_ACCOUNT_KEY', b2_account_key)

  cmd = [RESTIC] + global_options + subcmd + subcmd_options

  logger.info('$ %s', ' '.join(cmd))

  start = time.time()
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
      env=env)
  out, _ = p.communicate() #stderr is empty
  total = time.time() - start
  for k in out.split('\n'): logger.info(k)

  logger.info('restic %s took %s', subcmd, _human_time(total))

  if p.returncode != 0:
    logger.error('command exited with error state (%d)', p.returncode)

  return p.returncode == 0


def backup(directory, repository, global_options, hostname, backup_options,
    password, b2_account_id=None, b2_account_key=None):
  '''Performs the backup

  This command executes ``restic backup`` for the provided local directory on
  the remote repository.


  Parameters:

    directory (str): The path leading to the directory that is going to be
      backed up

    repository (str): The restic repository that will hold the backup. This can
      be either a local repository path or a BackBlaze B2 bucket name, duly
      prefixed by ``b2:``.

    global_options (list): A list of global options to pass to restic (like
      ``--limit-download`` or ``--limit-upload``) - don't include ``--repo`` as
      this will be included automatically

    hostname (str): The name of the host to use for backing-up

    backup_options (list): A list of backup options to pass to restic (like
      ``--exclude`` flags) - don't pass ``--hostname`` as this will be included
      automatically

    password (str): The restic repository password

    b2_account_id (str, Optional): The BackBlaze B2 account identifier. Must be
      set if ``repository`` starts with ``b2:``

    b2_account_key (str, Optional): The BackBlaze B2 key to use to run the
      backup. This key must have access to the specified bucket.
      set if ``repository`` starts with ``b2:``

  '''

  return run_restic(['--repo', repository] + global_options,
      'backup', ['--hostname', hostname] + backup_options, password,
      b2_account_id, b2_account_key)


def forget(repository, global_options, hostname, prune, keep, password,
    b2_account_id=None, b2_account_key=None):
  '''Performs the backup

  This command executes ``restic forget`` for the provided local directory on
  the remote repository.


  Parameters:

    repository (str): The restic repository that will hold the backup. This can
      be either a local repository path or a BackBlaze B2 bucket name, duly
      prefixed by ``b2:``.

    global_options (list): A list of global options to pass to restic (like
      ``--limit-download`` or ``--limit-upload``) - don't include ``--repo`` as
      this will be included automatically

    hostname (str): The name of the host to use for backing-up

    prune (bool): A flag indicating if we should prune while forgetting.
      Typicall, this should be ``True``.

    keep (dict): A dictionary containing the number of snapshots to keep per
      category. Valid values are 'last', 'hourly', 'daily', 'weekly',
      'monthly' and 'yearly'

    password (str): The restic repository password

    b2_account_id (str, Optional): The BackBlaze B2 account identifier. Must be
      set if ``repository`` starts with ``b2:``

    b2_account_key (str, Optional): The BackBlaze B2 key to use to run the
      backup. This key must have access to the specified bucket.
      set if ``repository`` starts with ``b2:``

  '''

  options = ['--prune'] if prune else []
  for key in keep:
    options += ['--keep-%s' % key, str(keep[key])]

  return run_restic(['--repo', repository] + global_options,
      'forget', ['--host', hostname] + options, password,
      b2_account_id, b2_account_key)


def forget(repository, global_options, password, b2_account_id=None,
    b2_account_key=None):
  '''Checks the sanity of a restic repository

  This procedure is recommended after each forget operation


  Parameters:

    repository (str): The restic repository that will hold the backup. This can
      be either a local repository path or a BackBlaze B2 bucket name, duly
      prefixed by ``b2:``.

    global_options (list): A list of global options to pass to restic (like
      ``--limit-download`` or ``--limit-upload``) - don't include ``--repo`` as
      this will be included automatically

    password (str): The restic repository password

    b2_account_id (str, Optional): The BackBlaze B2 account identifier. Must be
      set if ``repository`` starts with ``b2:``

    b2_account_key (str, Optional): The BackBlaze B2 key to use to run the
      backup. This key must have access to the specified bucket.
      set if ``repository`` starts with ``b2:``

  '''

  options = ['--check-unused']

  return run_restic(['--repo', repository] + global_options,
      'check', options, password, b2_account_id, b2_account_key)


def snapshots(repository, global_options, hostname, password,
    b2_account_id=None, b2_account_key=None):
  '''Lists current snapshots available

  Parameters:

    repository (str): The restic repository that will hold the backup. This can
      be either a local repository path or a BackBlaze B2 bucket name, duly
      prefixed by ``b2:``.

    global_options (list): A list of global options to pass to restic (like
      ``--limit-download`` or ``--limit-upload``) - don't include ``--repo`` as
      this will be included automatically

    hostname (str): The name of the host to use for backing-up

    password (str): The restic repository password

    b2_account_id (str, Optional): The BackBlaze B2 account identifier. Must be
      set if ``repository`` starts with ``b2:``

    b2_account_key (str, Optional): The BackBlaze B2 key to use to run the
      backup. This key must have access to the specified bucket.
      set if ``repository`` starts with ``b2:``

  '''

  return run_restic(['--repo', repository] + global_options,
      'snapshots', ['--host', hostname], password, b2_account_id,
      b2_account_key)
