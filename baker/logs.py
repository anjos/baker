#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Dump (optionless) script that retrieves logs from one of our containers"""

import os
import sys
from baker import qnap, utils


def main():

    from baker import reporter

    logger = reporter.setup_logger("baker", 2)

    nas = utils.retrieve_json_secret("nas/info.json")
    server = nas["server"]

    with qnap.session(server, nas["username"], nas["password"]) as session:

        existing = qnap.get_containers(session, server)
        existing = dict([(k["name"], k) for k in existing])

        if len(sys.argv) > 1:
            for k in sys.argv[1:]:
                if len(sys.argv) > 2:
                    print(">>>>>>>>>>>> %s <<<<<<<<<<<<<<" % k)
                print(
                    qnap.retrieve_logs(
                        session, server, existing[k]["id"], tail=1000
                    )["logs"]
                )

        else:
            print("usage: %s <container-name> [<container-name> ...]")
            print("  Existing container names:")
            for key in sorted(existing.keys()):
                print("  - %s (state: %s)" % (key, existing[key]["state"]))


if __name__ == "__main__":
    main()
