#!/usr/bin/env python


'''An interface to the restic command-line application'''


import os
import copy
import json
import datetime

import logging
logger = logging.getLogger(__name__)

from .utils import run_cmdline, which


RESTIC_BIN = which('restic')
logger.debug('Using restic from `%s\'', RESTIC_BIN)


def run_restic(global_options, subcmd, subcmd_options, password=None,
    cache=None):
  '''Runs restic on a contained environment, report output and status


  Runs the restic binary on the provided environment, capturing output and
  status exit code.


  Parameters:

    global_options (list): A list of global options to pass to restic

    subcmd (str): The subcommand to call

    subcmd_options (list): A list of subcommand specific options

    password (str, Optional): The restic repository password

    cache (str, Optional): The path to the cache directory to use for restic.
      If not set, use the XDG cache default (typically ~/.cache/restic)


  Returns:

    bool: ``True`` if the program returned 0 exit status (ran w/o problems)

  '''

  if not RESTIC_BIN:
    raise RuntimeError("The executable `restic' must be available " \
        "on your ${PATH}")

  env = copy.copy(os.environ)
  if password: env.setdefault('RESTIC_PASSWORD', password)

  if cache:
    global_options += ['--cache-dir', cache]

  cmd = [RESTIC_BIN] + global_options + [subcmd] + subcmd_options

  return run_cmdline(cmd, env)


def _assert_b2_setup(repo):
  '''Checks if B2 credentials are setup correctly'''

  if repo.startswith('b2:'):
    if 'B2_ACCOUNT_ID' not in os.environ:
      raise RuntimeError("You must setup ${B2_ACCOUNT_ID} to use a " \
          "BackBlaze B2 repository")
    if 'B2_ACCOUNT_KEY' not in os.environ:
      raise RuntimeError("You must setup ${B2_ACCOUNT_KEY} to use a " \
          "BackBlaze B2 repository")


def version():
  '''Returns the result of ``restic version``
  '''

  return run_restic([], 'version', [])


def init(repository, global_options, password, cache):
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

    cache (str): The path to the cache directory to use for restic. If not set,
      use the XDG cache default (typically ~/.cache/restic)

  '''

  _assert_b2_setup(repository)
  return run_restic(['--repo', repository] + global_options, 'init', [],
      password, cache)


def backup(directory, repository, global_options, hostname, backup_options,
    password, cache):
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

    cache (str): The path to the cache directory to use for restic. If not set,
      use the XDG cache default (typically ~/.cache/restic)

  '''

  _assert_b2_setup(repository)
  return run_restic(['--repo', repository] + global_options,
      'backup', ['--hostname', hostname] + backup_options + [directory],
      password, cache)


def forget(repository, global_options, hostname, prune, keep, password, cache):
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

    cache (str): The path to the cache directory to use for restic. If not set,
      use the XDG cache default (typically ~/.cache/restic)

  '''

  _assert_b2_setup(repository)

  options = ['--prune'] if prune else []
  for key in keep:
    options += ['--keep-%s' % key, str(keep[key])]

  return run_restic(['--repo', repository] + global_options,
      'forget', ['--host', hostname] + options, password, cache)


def check(repository, global_options, thorough, password, cache):
  '''Checks the sanity of a restic repository

  This procedure is recommended after each forget operation


  Parameters:

    repository (str): The restic repository that will hold the backup. This can
      be either a local repository path or a BackBlaze B2 bucket name, duly
      prefixed by ``b2:``.

    global_options (list): A list of global options to pass to restic (like
      ``--limit-download`` or ``--limit-upload``) - don't include ``--repo`` as
      this will be included automatically

    thorough (bool): If set to ``True``, then don't use cached data for a
      check. Otherwise, it does.

    password (str): The restic repository password

    cache (str): The path to the cache directory to use for restic. If not set,
      use the XDG cache default (typically ~/.cache/restic)

  '''

  _assert_b2_setup(repository)

  if thorough:
    options = ['--check-unused']
  else:
    options = ['--with-cache']
  return run_restic(['--repo', repository] + global_options,
      'check', options, password, cache)


def snapshots(repository, global_options, hostname, password, cache):
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

    cache (str): The path to the cache directory to use for restic. If not set,
      use the XDG cache default (typically ~/.cache/restic)


  Returns:

    list: A list of dictionaries with the properties of each snapshot following
    the specifications. The list is organized by snapshot date, the first being
    the oldest snapshot and the last the youngest.

  '''

  _assert_b2_setup(repository)

  output = run_restic(['--repo', repository, '--json'] + global_options,
      'snapshots', ['--host', hostname], password, cache)

  data = json.loads(output)

  # convert date/time representations for easier parsing
  for k in data:
    s = k['time'][:24]
    k['time'] = datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')

  return sorted(data, key=lambda k: k['time'])


def unlock(repository, global_options, password, cache, remove_all):
  '''Removes stale locks from a remote repository

  Parameters:

    repository (str): The restic repository that will hold the backup. This can
      be either a local repository path or a BackBlaze B2 bucket name, duly
      prefixed by ``b2:``.

    global_options (list): A list of global options to pass to restic (like
      ``--limit-download`` or ``--limit-upload``) - don't include ``--repo`` as
      this will be included automatically

    password (str): The restic repository password

    cache (str): The path to the cache directory to use for restic. If not set,
      use the XDG cache default (typically ~/.cache/restic)

    remove_all (bool): If we should remove all locks (including non-stale ones).
      This will pass the subcommand option ``--remove-all`` to restic


  Returns:

    str: The output of the command

  '''

  _assert_b2_setup(repository)
  unlock_options = ['--remove-all'] if remove_all else []
  return run_restic(['--repo', repository] + global_options, 'unlock',
      unlock_options, password, cache)


def rebuild_index(repository, global_options, password, cache):
  '''Rebuilds the index on an existing repository

  Parameters:

    repository (str): The restic repository that will hold the backup. This can
      be either a local repository path or a BackBlaze B2 bucket name, duly
      prefixed by ``b2:``.

    global_options (list): A list of global options to pass to restic (like
      ``--limit-download`` or ``--limit-upload``) - don't include ``--repo`` as
      this will be included automatically

    password (str): The restic repository password

    cache (str): The path to the cache directory to use for restic. If not set,
      use the XDG cache default (typically ~/.cache/restic)


  Returns:

    str: The output of the command

  '''

  _assert_b2_setup(repository)

  return run_restic(['--repo', repository] + global_options, 'rebuild-index',
      [], password, cache)


def prune(repository, global_options, password, cache):
  '''Prunes unreferenced objects on an existing repository

  Parameters:

    repository (str): The restic repository that will hold the backup. This can
      be either a local repository path or a BackBlaze B2 bucket name, duly
      prefixed by ``b2:``.

    global_options (list): A list of global options to pass to restic (like
      ``--limit-download`` or ``--limit-upload``) - don't include ``--repo`` as
      this will be included automatically

    password (str): The restic repository password

    cache (str): The path to the cache directory to use for restic. If not set,
      use the XDG cache default (typically ~/.cache/restic)


  Returns:

    str: The output of the command

  '''

  _assert_b2_setup(repository)

  return run_restic(['--repo', repository] + global_options, 'prune', [],
      password, cache)
