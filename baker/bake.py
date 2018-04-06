#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

"""Backs-up local folders on BackBlaze B2

Usage: %(prog)s [-v...] init [--b2-account-id=<id>] [--b2-account-key=<key>]
                [--hostname=<name>] [--cache=<dir>] [--overwrite]
                [--email --email-receiver=<name> [--email-receiver=<name> ...] --email-sender=<name> --email-username=<user> --email-password=<pwd> [--email-server=<host>] [--email-port=<port>]]
                <password> <config> [<config> ...]
       %(prog)s [-v...] update [--b2-account-id=<id>] [--b2-account-key=<key>]
                [--hostname=<name>] [--cache=<dir>] [--keep=<kept>]
                [--email --email-receiver=<name> [--email-receiver=<name> ...] --email-sender=<name> --email-username=<user> --email-password=<pwd> [--email-server=<host>] [--email-port=<port>]]
                [--run-daily-at=<hour>]
                <password> <config> [<config> ...]
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


Arguments:

  <password>  Restic repository password. This value will be applied to all
              configurations defined after it.
  <config>    A double composed of a local directory and a repository,
              separated by a pipe '|' symbol. Example "/data|b2:data". This
              double indicates that the local directory "/data" will be
              backed-up on the BackBlaze B2 bucket called "data".


Options:
  -h, --help                   Shows this help message and exits
  -V, --version                Prints the version and exits
  -v, --verbose                Increases the output verbosity level. May be
                               used multiple times
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
                               [default: 0|0|7|9|13|3]
  -d, --run-daily-at=<hour>    Runs the back-up job daily at the specified
                               time
  -o, --overwrite              During initialization of a new restic
                               repository, overwrites contents of an existing
                               directory in case any exist. Use this option
                               with care.
  -e, --email                  If set, e-mail agents responsible every time
                               action occurs
  -r, --email-sender=<name>    Name/e-mail of the person that will appear as
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

"""


import os
import sys
import time
import textwrap
import traceback
import pkg_resources

import logging
logger = logging.getLogger(__name__)

import schedule


def _send_message(subject_template, body_template_text, body_template_html,
    context, email):
  '''Sends an e-mail message or logs only'''

  from .reporter import Email, pluralize, format_datetime, humanize_time
  from .utils import get_size
  from jinja2 import Environment, PackageLoader, select_autoescape

  env = Environment(loader=PackageLoader(__name__, 'templates'),
      autoescape=select_autoescape(disabled_extensions=('txt',),
        default_for_string=True, default=True))

  # adds personalized filters for our templates
  env.filters['bake_pluralize'] = pluralize
  env.filters['du_dir'] = get_size
  env.filters['format_datetime'] = format_datetime
  env.filters['humanize_time'] = humanize_time

  # completes the context with package variables
  context['package'] = 'baker'
  context['version'] = pkg_resources.require('baker')[0].version

  subject = env.get_template(subject_template).render(**context)
  body_text = env.get_template(body_template_text).render(**context)

  if body_template_html is not None:
    body_html = env.get_template(body_template_html).render(**context)
  else:
    body_html = None

  sender = email.get('sender', 'nobody@example.com')
  receiver = email.get('receiver', ['nobody@example.com'])

  msg = Email(subject, body_text, body_html, sender, receiver)

  if email:
    msg.send(email['server'], email['port'], email['username'],
      email['password'])
  else:
    logger.info(msg.message())


def init(configs, password, cache, overwrite, hostname, email, b2):
  '''Initializes a new set of repositories based on the configs'''

  if b2:
    os.environ.setdefault('B2_ACCOUNT_ID', b2['id'])
    os.environ.setdefault('B2_ACCOUNT_KEY', b2['key'])

  from .restic import init as _init
  from .restic import backup, snapshots
  from .utils import get_size

  log = ''
  sizes = []
  snaps = []

  try:

    for k, (dire, repo) in enumerate(configs.items()):

      if repo.startswith('b2:'): # BackBlaze B2 repository
        from .b2 import list_buckets, remove_bucket, authorize_account, \
            create_bucket
        log += authorize_account(b2['id'], b2['key'])
        if repo[3:] in list_buckets():
          if overwrite:
            remove_bucket(repo[3:])
          else:
            raise RuntimeError("BackBlaze B2 bucket `%s' already exists " \
                "and you did not pass --overwrite" % (repo))
        log += create_bucket(repo[3:])

      else:
        if os.path.exists(repo):
          if os.listdir(repo):
            if overwrite:
              logger.info("Removing directory `%s' on user request", repo)
              import shutil
              shutil.rmtree(repo)
              os.makedirs(repo)
            else:
              raise RuntimeError("Directory `%s' already exists " \
                  "and you did not pass --overwrite" % (repo))
        else:
          os.makedirs(repo)

      log += _init(
          repository=repo,
          global_options=[],
          password=password,
          cache=cache,
          )

      log += backup(
          directory=dire,
          repository=repo,
          global_options=[],
          hostname=hostname,
          backup_options=[],
          password=password,
          cache=cache,
          )

      snaps += snapshots(
          repository=repo,
          global_options=[],
          hostname=hostname,
          password=password,
          cache=cache,
          )

      if repo.startswith('b2:'):
        from .b2 import get_bucket
        info = get_bucket(repo[3:])
        sizes.append(0) #info['totalSize']
      else:
        sizes.append(get_size(repo))

      context = dict(
          configs=configs,
          sizes=sizes,
          snapshots=snaps,
          cache=cache,
          log=log,
          hostname=hostname,
          )
      _send_message('init/subject_success.txt', 'init/body_success.txt',
          'init/body_success.html', context, email)

  except Exception as e:
    logger.error('Error at initialization:\n%s', traceback.format_exc())
    context = dict(
        configs=configs,
        trace=traceback.format_exc(),
        cache=cache,
        log=log,
        hostname=hostname,
        )
    _send_message('init/subject_error.txt', 'init/body_error.txt',
        'init/body_error.html', context, email)

  return log, sizes, snaps


def update(configs, password, cache, hostname, email, b2, keep, period):
  '''Runs a continuous job (never exists) for keeping the backup updated'''

  def job():
    '''The job that gets scheduled'''

    if b2:
      os.environ.setdefault('B2_ACCOUNT_ID', b2['id'])
      os.environ.setdefault('B2_ACCOUNT_KEY', b2['key'])

    from .restic import backup, forget, check, snapshots
    from .utils import get_size

    log = ''
    sizes = []
    snaps = []

    try:

      for dire, repo in configs.items():

        log += backup(
            directory=dire,
            repository=repo,
            global_options=[],
            hostname=hostname,
            backup_options=[],
            password=password,
            cache=cache,
            )

        log += forget(
            repository=repo,
            global_options=[],
            hostname=hostname,
            prune=True,
            keep=keep,
            password=password,
            cache=cache,
            )

        log += check(
            repository=repo,
            global_options=[],
            password=password,
            cache=cache,
            )

        if repo.startswith('b2:'):
          from .b2 import get_bucket
          info = get_bucket(repo[3:])
          sizes.append(0) #info['totalSize']
        else:
          from .utils import get_size
          sizes.append(get_size(repo))

        snaps += snapshots(
            repository=repo,
            global_options=[],
            hostname=hostname,
            password=password,
            cache=cache,
            )

      context = dict(
          configs=configs,
          sizes=sizes,
          snapshots=snaps,
          cache=cache,
          log=log,
          hostname=hostname,
          )
      _send_message('update/subject_success.txt', 'update/body_success.txt',
          'update/body_success.html', context, email)

    except Exception as e:
      logger.error('Error at update:\n%s', traceback.format_exc())
      context = dict(
          configs=configs,
          trace=traceback.format_exc(),
          cache=cache,
          log=log,
          hostname=hostname,
          )
      _send_message('update/subject_error.txt', 'update/body_error.txt',
          'update/body_error.html', context, email)

    return log, sizes, snaps


  if period is None:
    logger.info('Scheduling backup job to run only once')
    return job() #run once
  else:
    logger.info('Scheduling backup job to run every day at %s', period)
    schedule.every().day.at(period).do(job)

  while True:
    schedule.run_pending()
    time.sleep(600) #checks every 10 minutes


def main(user_input=None):

  if user_input is not None:
    argv = user_input
  else:
    argv = sys.argv[1:]

  import docopt
  import socket

  completions = dict(
      prog=os.path.basename(sys.argv[0]),
      version=pkg_resources.require('baker')[0].version,
      hostname=socket.gethostname(),
      )

  args = docopt.docopt(
      __doc__ % completions,
      argv=argv,
      version=completions['version'],
      )

  from .reporter import setup_logger
  logger = setup_logger('baker', args['--verbose'])

  from .restic import version as restic_version
  from .b2 import version as b2_version

  # log
  logger.info("Baker version %s (running on %s)",
      completions['version'], args['--hostname'])
  logger.info(" - %s", restic_version().split('\n')[0])
  logger.info(" - %s", b2_version().split('\n')[0])

  # do some commandline parsing
  config = dict([k.split('|') for k in args['<config>']])

  # B2 setup, if required
  b2 = {}
  for dire, repo in config.items():
    if repo.startswith('b2:'):
      # needs b2 authentication setup
      from .b2 import setup as b2_setup
      args['--b2-account-id'], args['--b2-account-key'] = b2_setup(
          args['--b2-account-id'], args['--b2-account-key']
          )
      b2['id'] = args['--b2-account-id']
      b2['key'] = args['--b2-account-key']
      logger.info("B2 account id/key parameters provided")
      break

  # check some config variables
  for dire, repo in config.items():
    assert os.path.exists(dire)
    logger.info(" - (folder) %s -> %s (repo)", dire, repo)

  # parse e-mail details
  email = {}
  if args['--email']: #sending e-mails
    logger.info('Sending **real** e-mails:')
    assert args['--email-sender'], 'You must set --email-sender to send ' \
        'e-mails'
    logger.info(' - Sender: %s', args['--email-sender'])
    assert args['--email-receiver'], 'You must set --email-receiver to send' \
        'e-mails'
    logger.info(' - Receivers: %s', ', '.join(args['--email-receiver']))
    assert args['--email-server'], 'You must set --email-server to send' \
        'e-mails'
    logger.info(' - Server: %s:%s', args['--email-server'], args['--email-port'])
    assert args['--email-port'], 'You must set --email-port to send' \
        'e-mails'
    assert args['--email-username'], 'You must set --email-username to send' \
        'e-mails'
    logger.info(' - Username: %s', args['--email-username'])
    assert args['--email-password'], 'You must set --email-password to send' \
        'e-mails'
    logger.info(' - Password: ********')
    email['sender'] = args['--email-sender']
    email['receiver'] = args['--email-receiver']
    email['server'] = args['--email-server']
    email['port'] = args['--email-port']
    email['username'] = args['--email-username']
    email['password'] = args['--email-password']
  else:
    logger.info("Only logging e-mails, **not** sending anything")

  # verify cache
  if args['--cache'] is not None:
    assert os.path.exists(args['--cache'])
    logger.info("Caching restic requests at: %s", args['--cache'])

  if args['init']:
    try:
      init(config, args['<password>'], args['--cache'], args['--overwrite'],
          args['--hostname'], email, b2)
    except Exception as e:
      raise RuntimeError('Unexpected error was not properly handled: %s' % \
          str(e))

  elif args['update']:

    keep_keys = ['last', 'hourly', 'daily', 'weekly', 'monthly', 'yearly']
    keep = dict(zip(keep_keys, [int(k) for k in args['--keep'].split('|')]))

    logger.info("Snapshot storage strategy (--keep flags):")
    for key, value in keep.items():
      logger.info(' - %s: %d', key.capitalize(), value)

    try:
      update(config, args['<password>'], args['--cache'], args['--hostname'],
          email, b2, keep, args['--run-daily-at'])
    except Exception as e:
      raise RuntimeError('Unexpected error was not properly handled: %s' % \
          str(e))

  return 0
