#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import print_function

import os
import sys
import time
import warnings
import tempfile
import subprocess

import logging
logger = logging.getLogger(__name__)

from .reporter import human_time


class TemporaryDirectory(object):
    """Create and return a temporary directory.  This has the same
    behavior as mkdtemp but can be used as a context manager.  For
    example:

        with TemporaryDirectory() as tmpdir:
            ...

    Upon exiting the context, the directory and everything contained
    in it are removed.
    """

    def __init__(self, suffix="", prefix="tmp", dir=None):
        self._closed = False
        self.name = None # Handle mkdtemp raising an exception
        self.name = tempfile.mkdtemp(suffix, prefix, dir)

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.name

    def cleanup(self, _warn=False):
        if self.name and not self._closed:
            try:
                self._rmtree(self.name)
            except (TypeError, AttributeError) as ex:
                # Issue #10188: Emit a warning on stderr
                # if the directory could not be cleaned
                # up due to missing globals
                if "None" not in str(ex):
                    raise
                print("ERROR: {!r} while cleaning up {!r}".format(ex, self,),
                      file=_sys.stderr)
                return
            self._closed = True
            if _warn:
                self._warn("Implicitly cleaning up {!r}".format(self),
                           ResourceWarning)

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def __del__(self):
        # Issue a ResourceWarning if implicit cleanup needed
        self.cleanup(_warn=True)

    # XXX (ncoghlan): The following code attempts to make
    # this class tolerant of the module nulling out process
    # that happens during CPython interpreter shutdown
    # Alas, it doesn't actually manage it. See issue #10188
    _listdir = staticmethod(os.listdir)
    _path_join = staticmethod(os.path.join)
    _isdir = staticmethod(os.path.isdir)
    _islink = staticmethod(os.path.islink)
    _remove = staticmethod(os.remove)
    _rmdir = staticmethod(os.rmdir)
    _warn = warnings.warn

    def _rmtree(self, path):
        # Essentially a stripped down version of shutil.rmtree.  We can't
        # use globals because they may be None'ed out at shutdown.
        for name in self._listdir(path):
            fullname = self._path_join(path, name)
            try:
                isdir = self._isdir(fullname) and not self._islink(fullname)
            except OSError:
                isdir = False
            if isdir:
                self._rmtree(fullname)
            else:
                try:
                    self._remove(fullname)
                except OSError:
                    pass
        try:
            self._rmdir(path)
        except OSError:
            pass


def which(program):
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


def run_cmdline(cmd, env=None):
  '''Runs a command on a environment, logs output and reports status


  Parameters:

    cmd (list): The command to run, with parameters separated on a list

    env (dict, Optional): Environment to use for running the program on. If not
      set, use :py:obj:`os.environ`.


  Returns:

    str: The standard output and error of the command being executed

  '''

  if env is None: env = os.environ

  prefix = '$ %s' % ' '.join(cmd)
  logger.debug(prefix)
  sys.stdout.write(prefix + '\n')

  start = time.time()
  out = b''

  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
      env=env)

  chunk_size = 1 << 13
  for chunk in iter(lambda: p.stdout.read(chunk_size), b''):
    sys.stdout.write(chunk.decode())
    out += chunk

  if p.wait() != 0:
    logger.error('Command output is:\n%s', out)
    raise RuntimeError("command `%s' exited with error state (%d)" % \
        (' '.join(cmd), p.returncode))

  total = time.time() - start

  suffix = 'command took %s' % human_time(total)
  sys.stdout.write(suffix + '\n')
  logger.debug(suffix)

  out = out.decode()

  return out


def get_size(start_path = '.'):
  '''Returns the total size of contents of the provided directory'''

  total_size = 0
  for dirpath, dirnames, filenames in os.walk(start_path):
    for f in filenames:
      fp = os.path.join(dirpath, f)
      total_size += os.path.getsize(fp)
  return total_size
