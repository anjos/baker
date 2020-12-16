#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Dump (optionless) script that just deployes all our containers"""

import os
from . import qnap, utils, reporter


def _delete_create(session, server, name, existing, options):

    if name in existing:
        if existing[name]["state"] == "running":
            qnap.stop_container(session, server, existing[name]["id"])
        qnap.remove_container(session, server, existing[name]["id"])

    retval = qnap.create_container(session, server, name, options)
    if options.get("autostart", True) == False:
        qnap.stop_container(session, server, retval["id"])


def main():

    logger = reporter.setup_logger("baker", 3)

    common_command = utils.retrieve_json_secret("baker/deploy.json")
    common_options = [
        '%s="%s"' % (k, v)
        for k, v in common_command.items()
        if k.startswith("-")
    ]
    command_arguments = ['"%s"' % k for k in common_command['<args>']]
    common_command = " ".join(common_options + command_arguments)
    nas = utils.retrieve_json_secret("nas/info.json")
    server = nas["server"]

    volumes = {
        "new": ["baker-cache:/cache"],
        "host": {
            "/Documents": dict(bind="/documents", ro=True),
            "/Pictures": dict(bind="/pictures", ro=True),
            "/Music": dict(bind="/music", ro=True),
        },
    }

    with qnap.session(server, nas["username"], nas["password"]) as session:

        existing = qnap.get_containers(session, server)
        existing = dict([(k["name"], k) for k in existing])

        # Use this one for tests
        options = dict(volume=volumes, autostart=False, command="-vvv --help",)
        # _delete_create(session, server, 'baker-help', existing, options)

        #### RECURRENT ACTIONS ####

        options = dict(
            volume=volumes,
            autostart=True,
            command='-vv update --email=onerror --run-daily-at="03:00" '
            + common_command,
        )
        _delete_create(session, server, "baker-update", existing, options)

        #### ONCE IN A TIME ACTIONS ####

        options = dict(
            autostart=False,
            volume=volumes,
            command="-vvv check --email=always " + common_command,
        )
        _delete_create(session, server, "baker-check", existing, options)

        options = dict(
            autostart=False,
            volume=volumes,
            command="-vv update --force-recovery --email=always " + common_command,
        )
        _delete_create(session, server, "baker-recover", existing, options)


if __name__ == "__main__":
    main()
