#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utilities to handle BackBlaze B2 via command-line"""

import os
import json
import copy

import logging

logger = logging.getLogger(__name__)

from .utils import run_cmdline, which, TemporaryDirectory


B2_BIN = which("b2")
logger.debug("Using b2 from `%s'", B2_BIN)


def run_b2(args, mask=None):
    """Runs the b2 binary with the provided arguments


  Parameters:

    args (list): List of arguments to pass to the ``b2`` binary

    mask (int, Optional): If set to a value that is different than ``None``,
      then we replace everything from the cmd list index ``[mask:]`` by
      asterisks.  This may be imoprtant to avoid passwords or keys to be shown
      on the screen or sent via email.


  Returns:

    str: Standard output and error

  """

    if not B2_BIN:
        raise RuntimeError(
            "The executable `b2' must be available on your ${PATH}"
        )
    return run_cmdline([B2_BIN] + args, mask=mask)


def version():
    """Returns the result of ``b2 version``
  """

    return run_b2(["version"])


def get_account_info():
    """Returns the current account information

  This function will return a dictionary with account information retrieved
  from the SQLite file kept by the b2 command-line program. It will return
  and empty dictionary if no authorization information is available.


  Returns:

    dict: The account information, if the user is logged-in

  """

    try:
        return json.loads(run_b2(["get-account-info"]))
    except RuntimeError as e:
        return None


def clear_account():
    """Logs off, removes the authorization file kept locally and all credentials
  """

    return run_b2(["clear-account"])


def authorize_account(account_id, key):
    """Runs the authorization procedure for the b2 cmdline tool


  Parameters:

    account_id (str): The BackBlaze B2 account identifier

    key (str): The BackBlaze B2 key to use to run the command. This key must
      have access to the specified bucket.

  """

    return run_b2(["authorize-account", account_id, key], mask=2)


def sync(bucket, path):
    """Synchronizes contents of the given path to the bucket

  This function is primarily for tests as it **destructively** syncs local
  folder contents to the remote bucket


  Parameters:

    bucket (str): The name of the bucket to use for sync'ing
    path (str): Local path to a directory whose contents will be synchronized
      with the bucket

  """

    return run_b2(
        ["sync", "--allowEmptySource", "--delete", path, "b2://%s" % bucket]
    )


def empty_bucket(name):
    """Empties the contents of a BackBlaze B2 bucket

  Follows the following implementation advice: https://help.backblaze.com/hc/en-us/articles/225556127-How-Can-I-Easily-Delete-All-Files-in-a-Bucket-


  Parameters:

    name (str): The name of the bucket to remove contents from


  """

    with TemporaryDirectory() as d:
        return sync(name, d)  # remove all contents


def get_bucket(name):
    """Returns information about a BackBlaze B2 bucket


  Parameters:

    name (str): The name of the bucket to remove


  Returns:

    dict: With the JSON contents returned by the ``get-bucket`` command.

  """

    # --showSize will include the size in version 1.1.0+
    return json.loads(run_b2(["get-bucket", "--showSize", name]))


def remove_bucket(name):
    """Removes a BackBlaze B2 bucket

  Follows the following implementation advice: https://help.backblaze.com/hc/en-us/articles/225556127-How-Can-I-Easily-Delete-All-Files-in-a-Bucket-


  Parameters:

    name (str): The name of the bucket to remove


  Returns:

    dict: With the JSON contents returned by the ``delete-bucket`` command. The
    snippet contains the deleted bucket information.

  """

    empty_bucket(name)
    return json.loads(run_b2(["delete-bucket", name]))


def create_bucket(name, tp="allPrivate"):
    """Creates a new (private) bucket


  Parameters:

    name (str): The name of the bucket to remove
    tp (str, Optional): Either ``allPrivate`` or ``allPublic``. Supported
      values are described at
      https://www.backblaze.com/b2/docs/b2_create_bucket.html

  """

    # from: https://www.backblaze.com/b2/docs/lifecycle_rules.html
    # check the end of the page for set recipes: here, we delete all
    # files deleted by restic after a one day period. According to this thread:
    # https://forum.restic.net/t/safe-to-change-b2-lifecycle-settings/59 it
    # should work w/o issues and saves space overall. The rule here applies to
    # all files on the bucket. Notice you can input many rules, so the
    # commandline utility expects a list.
    lifecycle_rules = [
        {
            "daysFromHidingToDeleting": 1,
            "daysFromUploadingToHiding": None,
            "fileNamePrefix": "",
        }
    ]

    return run_b2(
        [
            "create-bucket",
            "--lifecycleRules",
            json.dumps(lifecycle_rules),
            name,
            tp,
        ]
    )


def list_buckets():
    """List all available buckets


  Returns:

    dict: A dictionary of buckets available in which keys are bucket names and
    values are bucket properties. Each value contains two bucket properties:
    ID (hexadecimal string) and bucket type (either "allPublic" or
    "allPrivate").

  """

    out = run_b2(["list-buckets"])
    if out.endswith("\n"):
        out = out[:-1]
    objects = out.split("\n")
    objects = [k.split() for k in objects if k.strip()]
    return dict([(k[-1], k[:-1]) for k in objects])


def bucket_contents(name, folder=None):
    """List bucket contents


  Parameters:

    name (str): The name of the bucket to check
    path (str, Optional): Sub-folder within the bucket to check for contents


  Returns:

    list: A list containing the files on the given bucket and subfolder (if
    provided)

  """

    args = ["ls", name]
    if folder:
        cmd += [folder]
    out = run_b2(args)
    if out.endswith("\n"):
        out = out[:-1]
    return out.split("\n")


def setup(b2_id=None, b2_key=None):
    """Sets up authorization for BackBlaze B2 operations

  This method will setup the B2 infrastructure for restic and b2's command-line
  app so it works flawlessly taking into consideration:

    1. Values passed as parameters
    2. Previously authenticated sessions (~/.b2_info)
    3. b2's command-line app authorization files (~/.b2_auth)
    4. Environment variables B2_ACCOUNT_ID and B2_ACCOUNT_KEY

  It will then authorize the b2 command-line application and setup
  B2_ACCOUNT_ID and B2_ACCOUNT_KEY so that restic's command-line app works with
  the same tokens.


  Parameters:

    b2_id (str, Optional): The b2 account identifier
    b2_key (str, Optional): The b2 application key to use for the transactions


  Returns:

    str: The b2 account identifier
    str: The b2 application key

  """

    B2_AUTH_FILE = os.path.expanduser("~/.b2_auth")

    # 1. Values passed as parameters: re-authorized on provided tokens
    if b2_id and b2_key:
        clear_account()
        authorize_account(b2_id, b2_key)

    b2_info = get_account_info()

    # 2. Previously authenticated sessions
    if b2_info is not None:
        logger.info("B2 service is ready - using current authorization")

    # 3. Checks if the user has an auth file hanging around
    elif os.path.exists(B2_AUTH_FILE):
        logger.info("Using b2-auth file at `%s'...", B2_AUTH_FILE)
        with open(B2_AUTH_FILE, "rt") as f:
            b2_account_id, b2_account_key = f.readlines()
            authorize_account(b2_account_id.strip(), b2_account_key.strip())

    # 3. last resource, auth tokens are set on the environment
    elif "B2_ACCOUNT_ID" in os.environ and "B2_ACCOUNT_KEY" in os.environ:
        logger.info("Using b2-auth info at environment...")
        authorize_account(
            os.environ["B2_ACCOUNT_ID"], os.environ["B2_ACCOUNT_KEY"]
        )

    if b2_info is None:
        b2_info = get_account_info()
        if not b2_info:
            raise RuntimeError(
                "Required B2 backend could not be setup! You may "
                "either set the environment variables "
                "B2_ACCOUNT_ID/B2_ACCOUNT_KEY or call this method with the "
                "correct values"
            )

    # reset the enviroment to make sure we're in sync with restic's cmdline
    os.environ["B2_ACCOUNT_ID"] = b2_info["accountId"]
    os.environ["B2_ACCOUNT_KEY"] = b2_info["applicationKey"]

    return b2_info["accountId"], b2_info["applicationKey"]
