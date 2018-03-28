#!/usr/bin/env python


'''An interface to the restic command-line application'''


import os
import copy
import json

import logging
logger = logging.getLogger(__name__)

from .utils import run_cmdline, which


RESTIC_BIN = which('restic')
logger.info('Using restic from `%s\'', RESTIC_BIN)


def run_restic(global_options, subcmd, subcmd_options, password=None):
  '''Runs restic on a contained environment, report output and status


  Runs the restic binary on the provided environment, capturing output and
  status exit code.


  Parameters:

    global_options (list): A list of global options to pass to restic

    subcmd (str): The subcommand to call

    subcmd_options (list): A list of subcommand specific options

    password (str, Optional): The restic repository password


  Returns:

    bool: ``True`` if the program returned 0 exit status (ran w/o problems)

  '''

  assert RESTIC_BIN, "The executable `restic' must be available on your ${PATH}"

  env = copy.copy(os.environ)
  if password: env.setdefault('RESTIC_PASSWORD', password)

  cmd = [RESTIC_BIN] + global_options + [subcmd] + subcmd_options

  return run_cmdline(cmd, env)


def _assert_b2_setup(repo):
  '''Checks if B2 credentials are setup correctly'''

  if repo.startswith('b2:'):
    assert 'B2_ACCOUNT_ID' in os.environ, "You must setup ${B2_ACCOUNT_ID} " \
        "to use a BackBlaze B2 repository"
    assert 'B2_ACCOUNT_KEY' in os.environ, "You must setup ${B2_ACCOUNT_KEY}" \
        " to use a BackBlaze B2 repository"


def init(repository, global_options, password):
  '''Initializes a restic repository

  The repository may be local or sitting on a remote B2 bucket


  Parameters:

    repository (str): The restic repository that will hold the backup. This can
      be either a local repository path or a BackBlaze B2 bucket name, duly
      prefixed by ``b2:``.

    global_options (list): A list of global options to pass to restic (like
      ``--limit-download`` or ``--limit-upload``) - don't include ``--repo`` as
      this will be included automatically

    password (str): The restic repository password

  '''

  _assert_b2_setup(repository)
  return run_restic(['--repo', repository] + global_options, 'init', [],
      password)


def backup(directory, repository, global_options, hostname, backup_options,
    password):
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

  '''

  _assert_b2_setup(repository)
  return run_restic(['--repo', repository] + global_options,
      'backup', ['--hostname', hostname] + backup_options + [directory], password)


def forget(repository, global_options, hostname, prune, keep, password):
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
      'monthly' and 'yearly'. You may include all or just some of these.

    password (str): The restic repository password

  '''

  _assert_b2_setup(repository)

  options = ['--prune'] if prune else []
  for key in keep:
    options += ['--keep-%s' % key, str(keep[key])]

  return run_restic(['--repo', repository] + global_options,
      'forget', ['--host', hostname] + options, password)


def check(repository, global_options, password):
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

  '''

  _assert_b2_setup(repository)

  options = ['--check-unused']
  return run_restic(['--repo', repository] + global_options,
      'check', options, password)


def snapshots(repository, global_options, hostname, password):
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


  Returns:

    list: A list of dictionaries with the properties of each snapshot following
    the specifications

  '''

  _assert_b2_setup(repository)
  output = run_restic(['--repo', repository, '--json'] + global_options,
      'snapshots', ['--host', hostname], password)
  return json.loads(output)
