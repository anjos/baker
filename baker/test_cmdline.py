#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for baker cmdline tool"""


import os
import time
import tempfile

import pytest
import pkg_resources

from .reporter import StdoutCapture, LogCapture

from . import commands
from . import bake


SAMPLE_DIR1 = pkg_resources.resource_filename(
    __name__, os.path.join("data", "dir1")
)
SAMPLE_DIR2 = pkg_resources.resource_filename(
    __name__, os.path.join("data", "dir2")
)


def test_help():

    with pytest.raises(SystemExit), StdoutCapture():
        bake.main(["--help"])


def run_init(repo, b2):

    with tempfile.TemporaryDirectory() as cache:
        log, sizes, snaps = commands.init(
            {SAMPLE_DIR1: repo},
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )

    assert len(sizes) == 1
    assert len(snaps) == 1
    assert sizes[repo] != 0
    assert snaps[0]["paths"] == [SAMPLE_DIR1]
    assert "parent" not in snaps[0]  # it is the first snapshot of repository

    messages = log.split("\n")[:-1]  # removes last end-of-line

    if b2:
        # skip other details
        messages = messages[:1] + messages[-1:]

    assert messages[0].startswith("created restic repository")
    assert messages[0].endswith(repo)
    assert messages[-1].startswith("snapshot")
    assert messages[-1].endswith("saved")


def test_init_local():

    with tempfile.TemporaryDirectory() as d:
        run_init(d, {})


def run_init_error(repo, b2):

    with LogCapture("baker") as buf, tempfile.TemporaryDirectory() as cache:
        configs = {
            SAMPLE_DIR1: repo,
            SAMPLE_DIR2: repo,  # error - cannot backup on the same repo
        }
        log, sizes, snaps = commands.init(
            configs,
            "password",
            cache,
            False,
            "hostname",
            {"condition": "never"},
            b2,
        )

    assert "Error at initialization" in buf.read()


def test_init_error():

    with tempfile.TemporaryDirectory() as d:
        run_init_error(d, {})


def run_init_multiple(repo1, repo2, b2):

    from collections import OrderedDict

    configs = OrderedDict(
        [  # preserves order for tests
            (SAMPLE_DIR1, repo1),
            (SAMPLE_DIR2, repo2),
        ]
    )

    with tempfile.TemporaryDirectory() as cache:
        log, sizes, snaps = commands.init(
            configs,
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )

    assert len(sizes) == 2
    assert sizes[repo1] != 0
    assert sizes[repo2] != 0

    assert len(snaps) == 2
    assert snaps[0]["paths"] == [SAMPLE_DIR1]
    assert "parent" not in snaps[0]  # it is the first snapshot of repository
    assert snaps[1]["paths"] == [SAMPLE_DIR2]
    assert "parent" not in snaps[1]  # it is the first snapshot of repository

    messages = log.split("\n")[:-1]  # removes last end-of-line

    messages1 = messages[: int(len(messages) / 2)]
    messages2 = messages[int(len(messages) / 2) :]

    if b2:
        # skip other details
        messages1 = messages1[:1] + messages1[-1:]
        messages2 = messages2[:1] + messages2[-1:]

    assert messages1[0].startswith("created restic repository")
    assert messages1[0].endswith(repo1)
    assert messages1[-1].startswith("snapshot")
    assert messages1[-1].endswith("saved")

    assert messages2[0].startswith("created restic repository")
    assert messages2[0].endswith(repo2)
    assert messages2[-1].startswith("snapshot")
    assert messages2[-1].endswith("saved")


def test_init_multiple_local():

    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        run_init_multiple(d1, d2, {})


def run_init_cmdline(repo, options):

    with StdoutCapture() as buf, tempfile.TemporaryDirectory() as cache:
        retval = bake.main(
            options
            + [
                "-vvv",
                "init",
                "--overwrite",
                "--cache=%s" % cache,
                "--host=hostname",
                "password",
                "%s|%s" % (SAMPLE_DIR1, repo),
            ]
        )

    assert retval == 0
    assert "Successful initialization of" in buf.read()


def test_init_cmdline():

    with tempfile.TemporaryDirectory() as d:
        run_init_cmdline(d, [])


def run_update(repo, b2):

    with tempfile.TemporaryDirectory() as cache:
        log1, sizes1, snaps1 = commands.init(
            {SAMPLE_DIR1: repo},
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )
        log2 = commands.update(
            {SAMPLE_DIR1: repo},
            "password",
            cache,
            "hostname",
            {"condition": "never"},
            b2,
            {"last": 1},
            period=None,
            max_recoveries=0,
            force_recovery=False,
        )

    assert len(sizes1) == 1
    assert sizes1[repo] != 0
    assert len(snaps1) == 1
    assert "parent" not in snaps1[0]

    messages = log2.split("\n")[:-1]  # removes last end-of-line

    assert messages[7].startswith("snapshot")
    assert messages[7].endswith("saved")

    assert messages[8].startswith("Applying Policy: keep")

    assert SAMPLE_DIR1 in messages[12]


def test_update_local():

    with tempfile.TemporaryDirectory() as d:
        run_update(d, {})


def run_update_recover(repo, b2):

    with tempfile.TemporaryDirectory() as cache:
        log1, sizes1, snaps1 = commands.init(
            {SAMPLE_DIR1: repo},
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )
        log2 = commands.update(
            {SAMPLE_DIR1: repo},
            "password",
            cache,
            "hostname",
            {"condition": "never"},
            b2,
            {"last": 1},
            period=None,
            max_recoveries=1,
            force_recovery=True,
        )

    assert len(sizes1) == 1
    assert sizes1[repo] != 0
    assert len(snaps1) == 1
    assert "parent" not in snaps1[0]

    messages = log2.split("\n")[:-1]  # removes last end-of-line

    assert messages[0] == "successfully removed locks"
    assert messages[1] == "loading indexes..."
    assert messages[17].startswith("snapshot")
    assert messages[17].endswith("saved")
    assert messages[18] == "loading indexes..."
    assert messages[19] == "loading all snapshots..."
    assert messages[35] == "done"
    assert messages[36].startswith("Applying Policy: keep")
    assert SAMPLE_DIR1 in messages[40]


def test_update_recover():

    with tempfile.TemporaryDirectory() as d:
        run_update_recover(d, {})


def run_update_multiple(repo1, repo2, b2):

    from collections import OrderedDict

    configs = OrderedDict(
        [  # preserves order for tests
            (SAMPLE_DIR1, repo1),
            (SAMPLE_DIR2, repo2),
        ]
    )

    with tempfile.TemporaryDirectory() as cache:
        log1, sizes1, snaps1 = commands.init(
            configs,
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )
        log2 = commands.update(
            configs,
            "password",
            cache,
            "hostname",
            {"condition": "never"},
            b2,
            {"last": 1},
            period=None,
            max_recoveries=0,
            force_recovery=False,
        )

    assert len(sizes1) == 2
    assert sizes1[repo1] != 0
    assert sizes1[repo2] != 0
    assert len(snaps1) == 2
    assert "parent" not in snaps1[0]
    assert "parent" not in snaps1[1]

    split_index = log2.rfind("\nFiles:")
    messages1 = log2[:split_index].split("\n")
    messages2 = log2[split_index:].split("\n")

    assert messages1[7].startswith("snapshot")
    assert messages1[7].endswith("saved")
    assert SAMPLE_DIR1 in messages1[12]

    assert messages2[6].startswith("snapshot")
    assert messages2[6].endswith("saved")
    assert SAMPLE_DIR2 in messages2[11]


def test_update_local_multiple():

    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        run_update_multiple(d1, d2, {})


def run_update_error(repo1, repo2, b2):

    with LogCapture("baker") as buf, tempfile.TemporaryDirectory() as cache:
        configs = {
            SAMPLE_DIR1: repo1,
            SAMPLE_DIR2: repo2,
        }
        log1, sizes1, snaps1 = commands.init(
            configs,
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )
        configs = {
            SAMPLE_DIR1: repo1,
            SAMPLE_DIR2: repo2 + "-error",  # this directory does not exist
        }
        log2 = commands.update(
            configs,
            "password",
            cache,
            "hostname",
            {"condition": "never"},
            b2,
            {"last": 1},
            period=None,
            max_recoveries=0,
            force_recovery=False,
        )

    assert "ERROR during update" in buf.read()


def test_update_error():

    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        run_update_error(d1, d2, {})


def run_update_cmdline(repo, options):

    with StdoutCapture() as buf, tempfile.TemporaryDirectory() as cache:
        retval1 = bake.main(
            options
            + [
                "-vvv",
                "init",
                "--overwrite",
                "--cache=%s" % cache,
                "--host=hostname",
                "password",
                "%s|%s" % (SAMPLE_DIR1, repo),
            ]
        )
        retval2 = bake.main(
            options
            + [
                "-vvv",
                "update",
                "--host=hostname",
                "--cache=%s" % cache,
                "--keep=1|0|0|0|0|0",
                "password",
                "%s|%s" % (SAMPLE_DIR1, repo),
            ]
        )

    assert retval2 == 0
    assert "Successful update of" in buf.read()


def test_update_cmdline():

    with tempfile.TemporaryDirectory() as d:
        run_update_cmdline(d, [])


def run_check(repo, b2):

    with tempfile.TemporaryDirectory() as cache, LogCapture("baker") as buf:
        log1, sizes1, snaps1 = commands.init(
            {SAMPLE_DIR1: repo},
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )
        log2, sizes2, snaps2 = commands.check(
            {SAMPLE_DIR1: repo},
            "password",
            cache,
            "hostname",
            {"condition": "never"},
            b2,
            alarm=1000,
            period=None,
        )

    assert len(sizes1) == 1
    assert sizes1[repo] != 0
    assert len(snaps1) == 1
    assert len(sizes2) == 1
    assert sizes2[repo] != 0
    assert len(snaps2) == 1
    assert snaps1 == snaps2

    messages = log2.split("\n")[:-1]  # removes last end-of-line
    assert len(messages) == 0

    assert "Successful check of 1 repository" in buf.read()


def test_check_local():

    with tempfile.TemporaryDirectory() as d:
        run_check(d, {})


def run_check_alarm(repo, b2):

    with tempfile.TemporaryDirectory() as cache, LogCapture("baker") as buf:
        log1, sizes1, snaps1 = commands.init(
            {SAMPLE_DIR1: repo},
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )
        time.sleep(1.1)  # reach alarm condition
        log2, sizes2, snaps2 = commands.check(
            {SAMPLE_DIR1: repo},
            "password",
            cache,
            "hostname",
            {"condition": "never"},
            b2,
            alarm=1,
            period=None,
        )

    assert len(sizes1) == 1
    assert sizes1[repo] != 0
    assert len(snaps1) == 1
    assert len(sizes2) == 1
    assert sizes2[repo] != 0
    assert len(snaps2) == 1
    assert snaps1 == snaps2

    messages = log2.split("\n")[:-1]  # removes last end-of-line

    assert len(messages) == 0

    assert "ALARM condition (1 second) reached" in buf.read()


def test_check_alarm_local():

    with tempfile.TemporaryDirectory() as d:
        run_check_alarm(d, {})


def run_check_multiple(repo1, repo2, b2):

    from collections import OrderedDict

    configs = OrderedDict(
        [  # preserves order for tests
            (SAMPLE_DIR1, repo1),
            (SAMPLE_DIR2, repo2),
        ]
    )

    with tempfile.TemporaryDirectory() as cache, LogCapture("baker") as buf:
        log1, sizes1, snaps1 = commands.init(
            configs,
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )
        time.sleep(1.1)
        log2, sizes2, snaps2 = commands.check(
            configs,
            "password",
            cache,
            "hostname",
            {"condition": "never"},
            b2,
            alarm=1,
            period=None,
        )

    assert len(sizes1) == 2
    assert sizes1[repo1] != 0
    assert sizes1[repo2] != 0
    assert len(snaps1) == 2
    assert len(sizes2) == 2
    assert sizes2[repo1] != 0
    assert sizes2[repo2] != 0
    assert len(snaps2) == 2
    assert snaps1 == snaps2

    messages = log2.split("\n")[:-1]  # removes last end-of-line

    messages1 = messages[: int(len(messages) / 2)]
    messages2 = messages[int(len(messages) / 2) :]
    if b2:
        assert messages1[0] == "Using https://api.backblazeb2.com"
        messages1 = messages1[1:]
    if b2:
        assert messages2[0] == "Using https://api.backblazeb2.com"
        messages2 = messages2[1:]

    assert len(messages1) == 0
    assert len(messages2) == 0

    assert "ALARM condition (1 second) reached" in buf.read()


def test_check_local_multiple():

    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        run_check_multiple(d1, d2, {})


def run_check_error(repo1, repo2, b2):

    with LogCapture("baker") as buf, tempfile.TemporaryDirectory() as cache:
        configs = {
            SAMPLE_DIR1: repo1,
            SAMPLE_DIR2: repo2,
        }
        log1, sizes1, snaps1 = commands.init(
            configs,
            "password",
            cache,
            True,
            "hostname",
            {"condition": "never"},
            b2,
        )
        configs = {
            SAMPLE_DIR1: repo1,
            SAMPLE_DIR2: repo2 + "-error",  # this directory does not exist
        }
        log2, sizes2, snaps2 = commands.check(
            configs,
            "password",
            cache,
            "hostname",
            {"condition": "never"},
            b2,
            alarm=0,
            period=None,
        )

    assert "ERROR during check" in buf.read()


def test_check_error():

    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        run_check_error(d1, d2, {})


def run_check_cmdline(repo, options):

    with StdoutCapture() as buf, tempfile.TemporaryDirectory() as cache:
        retval1 = bake.main(
            options
            + [
                "-vvv",
                "init",
                "--overwrite",
                "--cache=%s" % cache,
                "--host=hostname",
                "password",
                "%s|%s" % (SAMPLE_DIR1, repo),
            ]
        )
        retval2 = bake.main(
            options
            + [
                "-vvv",
                "check",
                "--host=hostname",
                "--cache=%s" % cache,
                "--alarm=1000",
                "password",
                "%s|%s" % (SAMPLE_DIR1, repo),
            ]
        )

    assert retval2 == 0
    assert "Successful check of" in buf.read()


def test_check_cmdline():

    with tempfile.TemporaryDirectory() as d:
        run_check_cmdline(d, [])


def run_check_config(repo, options):

    with StdoutCapture() as buf, tempfile.TemporaryDirectory() as cache, tempfile.NamedTemporaryFile(
        mode="wt"
    ) as config:

        import json

        data = {
            "--verbose": 3,
            "--overwrite": True,
            "--cache": cache,
            "--alarm": "1000",
            "--host": "hostname",
            "<password>": "password",
            "<config>": [
                "%s|%s" % (SAMPLE_DIR1, repo),
            ],
        }
        data.update(options)
        json.dump(data, config)

        config.flush()

        retval1 = bake.main(["init", config.name])
        retval2 = bake.main(["check", config.name])

    assert retval2 == 0
    assert "Successful check of" in buf.read()


def test_check_config():

    with tempfile.TemporaryDirectory() as d:
        run_check_config(d, {})
