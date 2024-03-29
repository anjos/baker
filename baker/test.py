#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for baker"""


import os
import pkg_resources
import tempfile

import logging

logger = logging.getLogger(__name__)

from . import restic


SAMPLE_DIR = pkg_resources.resource_filename(
    __name__, os.path.join("data", "dir1")
)


def test_runner():

    out = restic.run_restic([], "version", [], "password")

    messages = out.split("\n")[:-1]  # removes last end-of-line

    assert len(messages) == 1
    assert messages[0].startswith("restic")  # restic 0.9.2
    assert "compiled with go" in messages[0]


def test_restic_init():

    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cache:
        out = restic.init(d, [], "password", cache)

    messages = out.split("\n")[:-1]  # removes last end-of-line
    assert len(messages) == 5
    assert messages[0].startswith("created restic repository")
    assert messages[0].endswith(d)


def test_restic_backup():

    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cache:
        restic.init(d, [], "password", cache)
        out = restic.backup(
            SAMPLE_DIR, d, [], "hostname", [], "password", cache
        )

    messages = out.split("\n")[:-1]  # removes last end-of-line
    assert len(messages) == 8
    assert messages[0].startswith("created new cache in")
    assert messages[0].endswith(cache)
    assert messages[1] == ""
    assert messages[-2].startswith("processed")
    assert messages[-1].startswith("snapshot")
    assert messages[-1].endswith("saved")


def test_restic_check():

    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cache:
        restic.init(d, [], "password", cache)
        restic.backup(SAMPLE_DIR, d, [], "hostname", [], "password", cache)
        out = restic.check(d, [], False, "password", cache)

    messages = out.split("\n")[:-1]  # removes last end-of-line
    assert len(messages) == 5
    assert messages[0] == "create exclusive lock for repository"
    assert messages[1] == "load indexes"
    assert messages[-1] == "no errors were found"


def test_restic_snapshots():

    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cache:
        restic.init(d, [], "password", cache)
        restic.backup(SAMPLE_DIR, d, [], "hostname", [], "password", cache)
        restic.backup(SAMPLE_DIR, d, [], "hostname", [], "password", cache)
        data = restic.snapshots(d, ["--json"], "hostname", "password", cache)

    # data is a list of dictionaries with the following fields
    #   * time: The time the snapshot was taken (as a datetime.datetime obj)
    #   * tree: The snapshot tree identifier?
    #   * paths: List of paths backed-up on that snapshot
    #   * hostname: The name of the host
    #   * username: The user identifier of the user that made the snapshot
    #   * uid: The user id for the snapshot file
    #   * gid: The groud id for snapshot file
    #   * id: The snapshot identifier
    #   * short_id: A shortened version of ``id``
    assert len(data) == 2
    assert data[0]["paths"] == [SAMPLE_DIR]
    assert data[0]["hostname"] == "hostname"
    assert data[1]["paths"] == [SAMPLE_DIR]
    assert data[1]["hostname"] == "hostname"


def test_restic_forget():

    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cache:
        restic.init(d, [], "password", cache)
        restic.backup(SAMPLE_DIR, d, [], "hostname", [], "password", cache)
        data1 = restic.snapshots(d, ["--json"], "hostname", "password", cache)
        restic.backup(SAMPLE_DIR, d, [], "hostname", [], "password", cache)
        restic.forget(d, [], "hostname", True, {"last": 1}, "password", cache)
        data2 = restic.snapshots(d, ["--json"], "hostname", "password", cache)

    # there are 2 backups which are nearly identical
    assert len(data2) == 1
    assert data2[0]["parent"] == data1[0]["id"]
    assert data2[0]["id"] != data1[0]["id"]


def test_restic_rebuild_index():

    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cache:
        restic.init(d, [], "password", cache)
        restic.backup(SAMPLE_DIR, d, [], "hostname", [], "password", cache)
        out = restic.rebuild_index(d, [], "password", cache)

    messages = out.split("\n")[:-1]  # removes last end-of-line
    assert len(messages) == 8
    assert messages[0] == "counting files in repo"
    assert messages[3] == "finding old index files"
    assert messages[5] == "remove 1 old index files"


def test_restic_prune():

    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cache:
        restic.init(d, [], "password", cache)
        restic.backup(SAMPLE_DIR, d, [], "hostname", [], "password", cache)
        out = restic.prune(d, [], "password", cache)

    messages = out.split("\n")[:-1]  # removes last end-of-line
    assert len(messages) == 22
    assert messages[0] == "counting files in repo"
    assert messages[-1] == "done"
