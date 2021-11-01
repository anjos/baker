#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

"""Backs-up local folders on BackBlaze B2

Usage: %(prog)s [-v...] init [--b2-account-id=<id>] [--b2-account-key=<key>]
                [--hostname=<name>] [--cache=<dir>] [--overwrite]
                [--email=<cond> --email-receiver=<name> [--email-receiver=<name> ...] --email-sender=<name> --email-username=<user> --email-password=<pwd> [--email-server=<host>] [--email-port=<port>]]
                <password> <config> [<config> ...]
       %(prog)s [-v...] update [--b2-account-id=<id>] [--b2-account-key=<key>]
                [--hostname=<name>] [--cache=<dir>] [--keep=<kept>]
                [--max-recoveries=<int>] [--force-recovery]
                [--email=<cond> --email-receiver=<name> [--email-receiver=<name> ...] --email-sender=<name> --email-username=<user> --email-password=<pwd> [--email-server=<host>] [--email-port=<port>]]
                [--run-daily-at=<hour>] <password> <config> [<config> ...]
       %(prog)s [-v...] check [--b2-account-id=<id>] [--b2-account-key=<key>]
                [--hostname=<name>] [--cache=<dir>] [--alarm=<seconds>]
                [--email=<cond> --email-receiver=<name> [--email-receiver=<name> ...] --email-sender=<name> --email-username=<user> --email-password=<pwd> [--email-server=<host>] [--email-port=<port>]]
                [--run-daily-at=<hour>] <password> <config> [<config> ...]
       %(prog)s [-v...] init <file>
       %(prog)s [-v...] update <file>
       %(prog)s [-v...] check <file>
       %(prog)s --help
       %(prog)s --version


Commands:

  init     Initializes (seeds or overwrites an existing one) with a new restic
           repository. Creates the first snapshot of the directory/directories
           to be backed-up. This procedure is not schedule-able as it can take
           long, but only needs to be done once per directory you want to
           back-up. Use it to initialize with the first snapshot, your new
           restic repository. If you set it up to do so, once the first
           snapshot is created, this app should send you an e-mail with the
           summary.
  update   Updates (or backs-up) continuously your local directory on the
           (remote) restic repository. After pre-seeding with the ``init``
           command above, you'll use this command (once a day or every N
           minutes) to keep your remote copy up-to-date with local changes. If
           set up to do so, this app will send you an e-mail everytime a new
           snapshot is created.
  check    Continuously monitor your (remote) restic repository. Use this
           command to check and inform you whether your repository is not being
           updated as you'd like. You can run this command in one of two modes:
           continuously if you pass the --run-daily-at flag, or for a single
           check/report if that is not set.


Arguments:

  <password>  Restic repository password. This value will be applied to all
              configurations defined after it.
  <config>    A double composed of a local directory and a repository,
              separated by a pipe '|' symbol. Example "/data|b2:data". This
              double indicates that the local directory "/data" will be
              backed-up on the BackBlaze B2 bucket called "data".
  <file>      A JSON formatted configuration file in which all doc-options are
              set. Using this alternative command-line system it is easier to
              pass command-line options and store working setups.  If the file
              name starts with "pass:", then the password-store will be used to
              retrieve the JSON file contents.


Options:
  -h, --help                   Shows this help message and exits
  -V, --version                Prints the version and exits
  -v, --verbose                Increases the output verbosity level. May be
                               used multiple times
  -a, --alarm=<seconds>        Set the check condition so that an alarm is
                               issued if the latest snapshot on the repository
                               is older than this number of seconds. A value of
                               zero disables the alarm [default: 0]
  -b, --b2-account-id=<id>     The BackBlaze B2 account identifier. Must be
                               set if ``config`` uses a BackBlaze bucket as
                               repository. Optionally, set the environment
                               variable B2_ACCOUNT_ID
  -B, --b2-account-key=<key>   The BackBlaze B2 key to use to run the backup.
                               This key must have access to the specified
                               bucket. Must be set if ``config`` uses a
                               BackBlaze bucket as repository. Optionally, set
                               the environment variable B2_ACCOUNT_KEY
  -c, --cache=<dir>            Directory where to save the restic cache to
                               avoid excessive accesses to network-based
                               repositories. Less important for local backups.
                               If not set, restic will use the XDG defaults
                               for the cache directory (typically
                               ${HOME}/.cache/restic)
  -H, --hostname=<name>        Use this name as hostname instead of the
                               environment's [default: %(hostname)s]
  -k, --keep=<kept>            A 6-tuple with integer values separated by a
                               pipe '|' symbol which indicate the number of
                               snapshots to keep for 'last', 'hourly', 'daily',
                               'weekly', 'monthly' and 'yearly' clean-ups. A
                               value of zero disables that option. Notice we
                               always prune the restic repository
                               [default: 0|0|7|8|12|2]
  -d, --run-daily-at=<hour>    Runs the back-up job daily at the specified
                               time
  -o, --overwrite              During initialization of a new restic
                               repository, overwrites contents of an existing
                               directory in case any exist. Use this option
                               with care.
  -e, --email=<cond>           If set, sents e-mails every time an action
                               finishes processing, depending on the set
                               condition.  Use ``never`` to never send e-mails.
                               Use ``always`` to always send e-mails. Use
                               ``onerror`` to send e-mails only if an error
                               condition is reached. [default: never]
  -s, --email-sender=<name>    Name/e-mail of the person that will appear as
                               the sender of the messages. This flag expects
                               entries in the format "John Doe <jd@ex.com>" or
                               "jd@ex.com"
  -r, --email-receiver=<name>  Name/e-mail of the person that will receive
                               messages generated by this application. Use this
                               option multiple times to indicate multiple
                               receivers of messages sent. This flag expects
                               entries in the format "John Doe <jd@ex.com>" or
                               "jd@ex.com".
  -u, --email-username=<name>  Username for the SMTP authentication and to be
                               used as the sender of e-mail messages
  -w, --email-password=<pwd>   Password for the SMTP authentication
  -S, --email-server=<host>    Name of the SMTP server to use for sending the
                               message [default: smtp.gmail.com]
  -P, --email-port=<port>      Port to use on the server [default: 587]
  -M, --max-recoveries=<int>   The maximum number of recovery attempts to try
                               after a failed update of a given repository
                               [default: 2]
  -R, --force-recovery         If set, then does not attempt an update of the
                               repository and starts with a recovery
                               immediately


Examples:

  1. Initializes a new (local) repository from the contents of /data:

     $ %(prog)s -vv init --hostname=my-host "password" "/data|/backup"

  2. Initializes a new (BackBlaze B2) repository from the contents of /data:

     $ %(prog)s -vv init --b2-account-id=yourid --b2-account-key=yourkey --hostname=my-host "password" "/data|b2:data"

  3. Updates (local) repository from the contents of /data:

     $ %(prog)s -vv update --hostname=my-host "password" "/data|/backup"

  4. Updates (BackBlaze B2) repository from the contents of /data:

     $ %(prog)s -vv update --b2-account-id=yourid --b2-account-key=yourkey --hostname=my-host "password" "/data|b2:data"

  5. Updates (local) repository from the contents of /data every day at 1AM
     (daemon mode):

     $ %(prog)s -vv update --run-daily-at='1:00' --hostname=my-host "password" "/data|/backup"

  6. Runs a single repository check, reports:

     $ %(prog)s -vv check --hostname=my-host "password" "/data|/backup"

  7. Runs a daily repository check, sends an alarm if did not backup for 2
     days (172800 seconds):

     $ %(prog)s -vv check --run-daily-at='9:00' --alarm=172800 --hostname=my-host "password" "/data|/backup"

"""


import os
import sys
import socket
import collections
import importlib.metadata

import logging

logger = logging.getLogger(__name__)

import docopt

from . import restic
from . import b2
from . import commands


def main(user_input=None):

    if user_input is not None:
        argv = user_input
    else:
        argv = sys.argv[1:]

    completions = dict(
        prog=os.path.basename(sys.argv[0]),
        version=importlib.metadata.version(__package__),
        hostname=socket.gethostname(),
    )

    args = docopt.docopt(
        __doc__ % completions,
        argv=argv,
        version=completions["version"],
    )

    if args["<file>"] is not None:
        # fill-in from file
        if args["<file>"].startswith("pass:"):
            from .utils import retrieve_json_secret

            secret_name = args["<file>"].split(":", 1)[1]
            options = retrieve_json_secret(secret_name)
        else:
            import json

            with open(args["<file>"], "rb") as f:
                options = json.load(f)

        args.update(options)

    from .reporter import setup_logger

    logger = setup_logger("baker", args["--verbose"])

    # log
    logger.info(
        "Baker version %s (running on %s)",
        completions["version"],
        args["--hostname"],
    )
    logger.info(" - %s", restic.version().split("\n")[0])
    logger.info(" - %s", b2.version().split("\n")[0])

    # do some commandline parsing
    config = collections.OrderedDict([k.split("|") for k in args["<config>"]])

    # B2 setup, if required
    b2_cred = {}
    for dire, repo in config.items():
        if repo.startswith("b2:"):
            # needs b2 authentication setup
            args["--b2-account-id"], args["--b2-account-key"] = b2.setup(
                args["--b2-account-id"], args["--b2-account-key"]
            )
            b2_cred["id"] = args["--b2-account-id"]
            b2_cred["key"] = args["--b2-account-key"]
            logger.info("B2 account id/key parameters provided")
            break

    # check some config variables
    for dire, repo in config.items():
        if not args["check"] and not os.path.exists(dire):
            raise RuntimeError("Path to backup `%s' does not exist" % dire)
        logger.info(" - (folder) %s -> %s (repo)", dire, repo)

    # parse e-mail details
    email = dict(
        condition=args["--email"],
        sender=args["--email-sender"],
        receiver=args["--email-receiver"],
        server=args["--email-server"],
        port=args["--email-port"],
        username=args["--email-username"],
        password=args["--email-password"],
    )

    if args["--email"] != "never":  # check
        logger.info("Sending **real** e-mails (%s):", args["--email"])
        if not args["--email-sender"]:
            raise RuntimeError("You must set --email-sender to send e-mails")
        logger.info(" - Sender: %s", args["--email-sender"])
        if not args["--email-receiver"]:
            raise RuntimeError("You must set --email-receiver to send e-mails")
        logger.info(" - Receivers: %s", ", ".join(args["--email-receiver"]))
        if not args["--email-server"]:
            raise RuntimeError("You must set --email-server to send e-mails")
        logger.info(
            " - Server: %s:%s", args["--email-server"], args["--email-port"]
        )
        if not args["--email-port"]:
            raise RuntimeError("You must set --email-port to send e-mails")
        if not args["--email-username"]:
            raise RuntimeError("You must set --email-username to send e-mails")
        logger.info(" - Username: %s", args["--email-username"])
        if not args["--email-password"]:
            raise RuntimeError("You must set --email-password to send e-mails")
        logger.info(" - Password: ********")
    else:
        logger.info("Only logging e-mails, **not** sending anything")

    # verify cache
    if args["--cache"] is not None:
        if not os.path.exists(args["--cache"]):
            raise RuntimeError(
                "Path to use for caching `%s' does not exist" % args["--cache"]
            )
        logger.info("Caching restic requests at: %s", args["--cache"])

    if args["init"]:
        try:
            commands.init(
                configs=config,
                password=args["<password>"],
                cache=args["--cache"],
                overwrite=args["--overwrite"],
                hostname=args["--hostname"],
                email=email,
                b2_cred=b2_cred,
            )
        except Exception as e:
            raise RuntimeError(
                "Unexpected error was not properly handled: %s" % str(e)
            )

    elif args["update"]:

        keep_keys = ["last", "hourly", "daily", "weekly", "monthly", "yearly"]
        keep = dict(zip(keep_keys, [int(k) for k in args["--keep"].split("|")]))

        logger.info("Snapshot storage strategy (--keep flags):")
        for key, value in keep.items():
            logger.info(" - %s: %d", key.capitalize(), value)

        try:
            commands.update(
                configs=config,
                password=args["<password>"],
                cache=args["--cache"],
                hostname=args["--hostname"],
                email=email,
                b2_cred=b2_cred,
                keep=keep,
                period=args["--run-daily-at"],
                max_recoveries=int(args["--max-recoveries"]),
                force_recovery=args["--force-recovery"],
            )
        except Exception as e:
            raise RuntimeError(
                "Unexpected error was not properly handled: %s" % str(e)
            )

    elif args["check"]:

        try:
            commands.check(
                configs=config,
                password=args["<password>"],
                cache=args["--cache"],
                hostname=args["--hostname"],
                email=email,
                b2_cred=b2_cred,
                alarm=int(args["--alarm"]),
                period=args["--run-daily-at"],
            )
        except Exception as e:
            raise RuntimeError(
                "Unexpected error was not properly handled: %s" % str(e)
            )

    return 0
