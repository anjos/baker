#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import json
import time
import copy
import subprocess

import logging

logger = logging.getLogger(__name__)

from .reporter import human_time


def retrieve_json_secret(key):
    """Retrieves a secret in JSON format from password-store"""

    logger.info("Retrieving '%s' from password-store...", key)
    p = subprocess.Popen(
        ["pass", "show", key], stdin=sys.stdin, stdout=subprocess.PIPE
    )
    return json.loads(p.communicate()[0].strip())


def run_cmdline(cmd, env=None, mask=None):
    """Runs a command on a environment, logs output and reports status


  Parameters:

    cmd (list): The command to run, with parameters separated on a list

    env (dict, Optional): Environment to use for running the program on. If not
      set, use :py:obj:`os.environ`.

    mask (int, Optional): If set to a value that is different than ``None``,
      then we replace everything from the cmd list index ``[mask:]`` by
      asterisks.  This may be imoprtant to avoid passwords or keys to be shown
      on the screen or sent via email.


  Returns:

    str: The standard output and error of the command being executed

  """

    if env is None:
        env = os.environ

    cmd_log = cmd
    if mask:
        cmd_log = copy.copy(cmd)
        for k in range(mask, len(cmd)):
            cmd_log[k] = "*" * len(cmd_log[k])
    logger.info("$ %s" % " ".join(cmd_log))

    start = time.time()
    out = b""

    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
    )

    chunk_size = 1 << 13
    lineno = 0
    for chunk in iter(lambda: p.stdout.read(chunk_size), b""):
        decoded = chunk.decode()
        while "\n" in decoded:
            pos = decoded.index("\n")
            logger.debug("%03d: %s" % (lineno, decoded[:pos]))
            decoded = decoded[pos + 1 :]
            lineno += 1
        out += chunk

    if p.wait() != 0:
        logger.error("Command output is:\n%s", out.decode())
        raise RuntimeError(
            "command `%s' exited with error state (%d)"
            % (" ".join(cmd_log), p.returncode)
        )

    total = time.time() - start

    logger.info("command took %s" % human_time(total))

    out = out.decode()

    return out


def get_size(path="."):
    """Returns the total size (in bytes) of contents of the provided directory"""

    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)

    return total_size
