#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

"""Commands used in our cmdline frontend"""

import os
import time
import shutil
import datetime
import traceback
import importlib.metadata

import logging

logger = logging.getLogger(__name__)

import schedule
import jinja2

from . import utils
from . import restic
from . import reporter
from . import b2


import logging

logger = logging.getLogger(__name__)


def _ordinal(n):
    return "%d%s" % (
        n,
        "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
    )


def _send_message(
    subject_template,
    body_template_text,
    body_template_html,
    context,
    email,
    error,
):
    """Sends an e-mail message or logs only"""

    env = jinja2.Environment(
        loader=jinja2.PackageLoader(__package__, "templates"),
        autoescape=jinja2.select_autoescape(
            disabled_extensions=("txt",), default_for_string=True, default=True
        ),
    )

    # adds personalized filters for our templates
    env.filters["bake_pluralize"] = reporter.pluralize
    env.filters["du_dir"] = utils.get_size
    env.filters["format_datetime"] = reporter.format_datetime
    env.filters["humanize_time"] = reporter.humanize_time
    env.filters["summarize_seconds"] = reporter.summarize_seconds
    env.filters["humanize_bytes"] = reporter.humanize_bytes

    # completes the context with package variables
    context["package"] = "baker"
    context["version"] = importlib.metadata.version(__package__)

    subject = env.get_template(subject_template).render(**context)
    body_text = env.get_template(body_template_text).render(**context)

    if body_template_html is not None:
        body_html = env.get_template(body_template_html).render(**context)
    else:
        body_html = None

    sender = email.get("sender", "nobody@example.com")
    receiver = email.get("receiver", ["nobody@example.com"])

    msg = reporter.Email(subject, body_text, body_html, sender, receiver)

    if ("condition" in email) and (
        (email["condition"] == "always")
        or (email["condition"] == "onerror" and error)
    ):
        msg.send(
            email["server"], email["port"], email["username"], email["password"]
        )
    else:
        logger.debug(msg.message())


def init(configs, password, cache, overwrite, hostname, email, b2_cred):
    """Initializes a new set of repositories based on the configs"""

    if b2_cred:
        os.environ.setdefault("B2_ACCOUNT_ID", b2_cred["id"])
        os.environ.setdefault("B2_ACCOUNT_KEY", b2_cred["key"])

    log = ""
    sizes = {}
    snapshots = []

    try:

        for k, (dire, repo) in enumerate(configs.items()):

            if repo.startswith("b2:"):  # BackBlaze B2 repository
                log += b2.authorize_account(b2_cred["id"], b2_cred["key"])
                if repo[3:] in b2.list_buckets():
                    if overwrite:
                        b2.remove_bucket(repo[3:])
                    else:
                        raise RuntimeError(
                            "BackBlaze B2 bucket `%s' already exists "
                            "and you did not pass --overwrite" % (repo)
                        )
                log += b2.create_bucket(repo[3:])

            else:
                if os.path.exists(repo):
                    if os.listdir(repo):
                        if overwrite:
                            logger.info(
                                "Removing directory `%s' on user request", repo
                            )
                            shutil.rmtree(repo)
                            os.makedirs(repo)
                        else:
                            raise RuntimeError(
                                "Directory `%s' already exists "
                                "and you did not pass --overwrite" % (repo)
                            )
                else:
                    os.makedirs(repo)

            log += restic.init(
                repository=repo,
                global_options=[],
                password=password,
                cache=cache,
            )

            log += restic.backup(
                directory=dire,
                repository=repo,
                global_options=[],
                hostname=hostname,
                backup_options=[],
                password=password,
                cache=cache,
            )

            snapshots += restic.snapshots(
                repository=repo,
                global_options=[],
                hostname=hostname,
                password=password,
                cache=cache,
            )

            if repo.startswith("b2:"):
                info = b2.get_bucket(repo[3:])
                sizes[repo] = info["totalSize"]
            else:
                sizes[repo] = utils.get_size(repo)

            context = dict(
                configs=configs,
                sizes=sizes,
                snapshots=snapshots,
                cache=cache,
                log=log,
                hostname=hostname,
            )
            _send_message(
                "init/subject_success.txt",
                "init/body_success.txt",
                "init/body_success.html",
                context,
                email,
                error=False,
            )

    except Exception as e:
        logger.error("Error at initialization:\n%s", traceback.format_exc())
        context = dict(
            configs=configs,
            trace=traceback.format_exc(),
            cache=cache,
            log=log,
            hostname=hostname,
        )
        _send_message(
            "init/subject_error.txt",
            "init/body_error.txt",
            "init/body_error.html",
            context,
            email,
            error=True,
        )

    return log, sizes, snapshots


def _do_update(
    dire,
    repo,
    password,
    cache,
    hostname,
    email,
    keep,
    max_recoveries,
    recovery=0,
):
    """Runs a single update job on a specific repository

    If the job fails, starts a number of recovery procedures on the same
    repository, until it is recovered or a maximum number of tries is reached.


    Parameters
    ==========

    dire : str
        The directory to be backed-up

    repo : str
        The remote repository (bucket) where the directory is going to be
        backed-up

    password : str
        The encryption password

    cache : str
        Path leading to the cache directory used by the application

    hostname : str
        The hostname that will be used on the bucket

    email : dict
        A dictionary configuration for e-mail sending.  This dictionary
        contains user credentials for the e-mail server and information on when
        to send e-mails (e.g. only on errors, or always).

    keep : str
        The keeping policy to be used during pruning operation for the backup

    max_recoveries : int
        The maximum number of recoveries to attempt

    recovery : int
        The current recovery attempt


    Returns
    =======

    error : bool
        A boolean indicating if there was an error

    log : str
        The log of operations

    """

    error = False
    log = ""

    try:

        if recovery > 0:
            logger.info("Start %s recovery attempt -- max of %d (%s -> %s)",
                    _ordinal(recovery), max_recoveries, dire, repo)

            log += restic.unlock(
                repository=repo,
                global_options=[],
                password=password,
                cache=cache,
                remove_all=False,  # only stale lock removal
            )

            log += restic.rebuild_index(
                repository=repo,
                global_options=[],
                password=password,
                cache=cache,
            )
        else:
            logger.info("Start back-up (%s -> %s)", dire, repo)

        log += restic.backup(
            directory=dire,
            repository=repo,
            global_options=[],
            hostname=hostname,
            backup_options=[],
            password=password,
            cache=cache,
        )

        if recovery > 0:
            log += restic.prune(
                repository=repo,
                global_options=[],
                password=password,
                cache=cache,
            )

        log += restic.forget(
            repository=repo,
            global_options=[],
            hostname=hostname,
            prune=True,
            keep=keep,
            password=password,
            cache=cache,
        )

        log += restic.check(
            repository=repo,
            global_options=[],
            thorough=bool(recovery),
            password=password,
            cache=cache,
        )

        if recovery > 0:
            # if we are recovering, it is nice to know that it went well
            context = dict(
                configs={dire:repo},
                cache=cache,
                log=log,
                hostname=hostname,
                recovery=_ordinal(recovery),
            )
            _send_message(
                "update/subject_success.txt",
                "update/body_success.txt",
                "update/body_success.html",
                context,
                email,
                error=True,  # send 'onerror' or 'always'
            )
            logger.info("Finished recovery (%s -> %s)", dire, repo)

        else:
            logger.info("Finished back-up (%s -> %s)", dire, repo)


    except Exception as e:
        if recovery > 0:
            logger.error(
                "Error at %s recovery attempt:\n%s",
                _ordinal(recovery),
                traceback.format_exc(),
            )
        else:
            logger.error("Error at update:\n%s", traceback.format_exc())

        context = dict(
            configs={dire:repo},
            trace=traceback.format_exc(),
            cache=cache,
            log=log,
            hostname=hostname,
            recovery=False if (recovery == 0) else _ordinal(recovery),
        )
        _send_message(
            "update/subject_error.txt",
            "update/body_error.txt",
            "update/body_error.html",
            context,
            email,
            error=True,  # send 'onerror' or 'always'
        )

        if recovery < max_recoveries:
            # tries again
            e, l = _do_update(
                dire,
                repo,
                password,
                cache,
                hostname,
                email,
                keep,
                max_recoveries=max_recoveries,
                recovery=recovery + 1,
            )
            error |= e
            log += l
        else:
            # something requires attention here, stop trying recoveries
            error = True

    return error, log


def update(
    configs,
    password,
    cache,
    hostname,
    email,
    b2_cred,
    keep,
    period,
    max_recoveries,
    force_recovery,
):
    """Runs a continuous job (never exits) for keeping the backup updated"""

    def job():
        """The job that gets scheduled"""

        if b2_cred:
            os.environ.setdefault("B2_ACCOUNT_ID", b2_cred["id"])
            os.environ.setdefault("B2_ACCOUNT_KEY", b2_cred["key"])

        error = False
        log = ""

        for dire, repo in configs.items():

            e, l = _do_update(
                dire,
                repo,
                password,
                cache,
                hostname,
                email,
                keep,
                max_recoveries,
                recovery = 0 if not force_recovery else 1,
            )
            error |= e
            log += l

        # sends one e-mail with the whole logs for the procedure
        context = dict(
            configs=configs,
            cache=cache,
            log=log,
            hostname=hostname,
            recovery=False,
        )
        _send_message(
            "update/subject_success.txt",
            "update/body_success.txt",
            "update/body_success.html",
            context,
            email,
            error=False,  # send only if 'always' context is set
        )

        return log

    if period is None:
        wait = 15
        logger.info("Scheduling backup job to run only once")
        logger.info("Waiting %d seconds before starting...", wait)
        time.sleep(wait)
        return job()  # run once
    else:
        logger.info("Scheduling backup job to run every day at %s", period)
        schedule.every().day.at(period).do(job)

    while True:
        schedule.run_pending()
        time.sleep(600)  # checks every 10 minutes


def check(configs, password, cache, hostname, email, b2_cred, alarm, period):
    """Runs a continuous job (never exits) for checking health of repositories"""

    def job():
        """The job that gets scheduled"""

        if b2_cred:
            os.environ.setdefault("B2_ACCOUNT_ID", b2_cred["id"])
            os.environ.setdefault("B2_ACCOUNT_KEY", b2_cred["key"])

        log = ""
        sizes = {}
        snapshots = []

        try:

            alarm_condition = False

            for dire, repo in configs.items():

                if period is None:  # calling a single time
                    if repo.startswith("b2:"):  # BackBlaze B2 repository
                        log += b2.authorize_account(
                            b2_cred["id"], b2_cred["key"]
                        )

                    if repo.startswith("b2:"):
                        info = b2.get_bucket(repo[3:])
                        sizes[repo] = info["totalSize"]
                    else:
                        sizes[repo] = utils.get_size(repo)

                snapshots += restic.snapshots(
                    repository=repo,
                    global_options=[],
                    hostname=hostname,
                    password=password,
                    cache=cache,
                )

                delta = datetime.datetime.now() - snapshots[-1]["time"]
                if alarm > 0 and delta.total_seconds() > alarm:
                    alarm_condition = True

            context = dict(
                configs=configs,
                sizes=sizes,
                snapshots=snapshots,
                cache=cache,
                log=log,
                hostname=hostname,
            )

            if alarm_condition:
                context["alarm"] = alarm
                _send_message(
                    "check/subject_alarm.txt",
                    "check/body_alarm.txt",
                    "check/body_alarm.html",
                    context,
                    email,
                    error=True,
                )

            else:
                # it is a single check, always send an e-mail
                _send_message(
                    "check/subject_success.txt",
                    "check/body_success.txt",
                    "check/body_success.html",
                    context,
                    email,
                    error=False,
                )

        except Exception as e:
            logger.error("Error at update:\n%s", traceback.format_exc())
            context = dict(
                configs=configs,
                trace=traceback.format_exc(),
                cache=cache,
                log=log,
                hostname=hostname,
            )
            _send_message(
                "check/subject_error.txt",
                "check/body_error.txt",
                "check/body_error.html",
                context,
                email,
                error=True,
            )

        return log, sizes, snapshots

    if period is None:
        wait = 15
        logger.info("Scheduling check job to run only once")
        logger.info("Waiting %d seconds before starting...", wait)
        time.sleep(wait)
        return job()  # run once
    else:
        logger.info("Scheduling check job to run every day at %s", period)
        schedule.every().day.at(period).do(job)

    while True:
        schedule.run_pending()
        time.sleep(600)  # checks every 10 minutes
