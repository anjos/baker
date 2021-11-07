#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for b2 infrastructure"""


import os
import uuid
import shutil
import pkg_resources
import tempfile
import logging

logger = logging.getLogger(__name__)

import collections

SampleData = collections.namedtuple("SampleData", ["bucket", "path"])

import pytest

from . import b2
from . import restic


@pytest.fixture()
def sample_data1():

    sample = SampleData(
        bucket="baker-test-" + str(uuid.uuid4())[:8],
        path=pkg_resources.resource_filename(
            __package__, os.path.join("data", "dir1")
        ),
    )

    b2.setup()

    # Creates test buckets with a given known prefix (and a random bit)
    b2.create_bucket(sample.bucket)

    yield sample

    shutil.rmtree(sample.bucket, ignore_errors=True)
    b2.remove_bucket(sample.bucket)


@pytest.fixture()
def sample_data2():

    sample = SampleData(
        bucket="baker-test-" + str(uuid.uuid4())[:8],
        path=pkg_resources.resource_filename(
            __package__, os.path.join("data", "dir2")
        ),
    )

    b2.setup()

    # Creates test buckets with a given known prefix (and a random bit)
    b2.create_bucket(sample.bucket)

    yield sample

    shutil.rmtree(sample.bucket, ignore_errors=True)
    b2.remove_bucket(sample.bucket)


def test_list_buckets(sample_data1):

    output = b2.list_buckets()
    assert sample_data1.bucket in output


def test_get_bucket(sample_data1):

    output = b2.get_bucket(sample_data1.bucket)
    assert "totalSize" in output


def test_list_bucket_contents(sample_data1):

    # Syncs our test directory with the bucket
    b2.sync(sample_data1.bucket, sample_data1.path)

    output = b2.bucket_contents(sample_data1.bucket)
    assert "example.txt" in output


def test_restic_init(sample_data1):

    repo = "b2:%s" % sample_data1.bucket

    with tempfile.TemporaryDirectory() as cache:
        out = restic.init(repo, [], "password", cache)

    messages = out.split("\n")[:-1]  # removes last end-of-line
    assert len(messages) == 5
    assert messages[0].startswith("created restic repository")
    assert messages[0].endswith(sample_data1.bucket)
    assert "config" in b2.bucket_contents(sample_data1.bucket)


def test_restic_backup(sample_data1):

    b2.empty_bucket(sample_data1.bucket)
    repo = "b2:%s" % sample_data1.bucket

    with tempfile.TemporaryDirectory() as cache:
        restic.init(repo, [], "password", cache)
        out = restic.backup(
            sample_data1.path, repo, [], "hostname", [], "password", cache
        )

    messages = out.split("\n")[:-1]  # removes last end-of-line
    assert len(messages) == 8
    assert messages[0].startswith("no parent snapshot found")
    assert messages[1] == ""
    assert messages[-2].startswith("processed")
    assert messages[-1].startswith("snapshot")
    assert messages[-1].endswith("saved")


def test_restic_check(sample_data1):

    b2.empty_bucket(sample_data1.bucket)
    repo = "b2:%s" % sample_data1.bucket

    with tempfile.TemporaryDirectory() as cache:
        restic.init(repo, [], "password", cache)
        restic.backup(
            sample_data1.path, repo, [], "hostname", [], "password", cache
        )
        out = restic.check(repo, [], True, "password", cache)

    messages = out.split("\n")[:-1]  # removes last end-of-line
    assert len(messages) == 8
    assert messages[0].startswith("using temporary cache in %s" % cache)
    assert messages[1] == "create exclusive lock for repository"
    assert messages[2] == "load indexes"
    assert messages[-1] == "no errors were found"


def test_restic_snapshots(sample_data1):

    repo = "b2:%s" % sample_data1.bucket

    with tempfile.TemporaryDirectory() as cache:
        restic.init(repo, [], "password", cache)
        restic.backup(
            sample_data1.path, repo, [], "hostname", [], "password", cache
        )
        restic.backup(
            sample_data1.path, repo, [], "hostname", [], "password", cache
        )
        data = restic.snapshots(repo, ["--json"], "hostname", "password", cache)

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
    assert data[0]["paths"] == [sample_data1.path]
    assert data[0]["hostname"] == "hostname"
    assert data[1]["paths"] == [sample_data1.path]
    assert data[1]["hostname"] == "hostname"


def test_restic_forget(sample_data1):

    repo = "b2:%s" % sample_data1.bucket

    with tempfile.TemporaryDirectory() as cache:
        restic.init(repo, [], "password", cache)
        restic.backup(
            sample_data1.path, repo, [], "hostname", [], "password", cache
        )
        data1 = restic.snapshots(
            repo, ["--json"], "hostname", "password", cache
        )
        restic.backup(
            sample_data1.path, repo, [], "hostname", [], "password", cache
        )
        restic.forget(
            repo, [], "hostname", True, {"last": 1}, "password", cache
        )
        data2 = restic.snapshots(
            repo, ["--json"], "hostname", "password", cache
        )

    # there are 2 backups which are nearly identical
    assert len(data2) == 1
    assert data2[0]["parent"] == data1[0]["id"]
    assert data2[0]["id"] != data1[0]["id"]


def _get_b2_info():

    info = b2.get_account_info()
    return {"id": info["accountId"], "key": info["applicationKey"]}


def test_cmdline_init(sample_data1):

    # Retrieve credentials
    from .test_cmdline import run_init

    run_init("%s" % sample_data1.bucket, _get_b2_info())


def test_cmdline_init_error(sample_data1):

    from .test_cmdline import run_init_error

    run_init_error("%s" % sample_data1.bucket, _get_b2_info())


def test_cmdline_init_multiple(sample_data1, sample_data2):

    from .test_cmdline import run_init_multiple

    run_init_multiple(
        "%s" % sample_data1.bucket,
        "%s" % sample_data2.bucket,
        _get_b2_info(),
    )


def test_cmdline_init_cmdline(sample_data1):

    from .test_cmdline import run_init_cmdline

    run_init_cmdline("%s" % sample_data1.bucket, [])


def test_cmdline_update(sample_data1):

    from .test_cmdline import run_update

    run_update("%s" % sample_data1.bucket, _get_b2_info())


def test_cmdline_update_recover(sample_data1):

    from .test_cmdline import run_update_recover

    run_update_recover("%s" % sample_data1.bucket, _get_b2_info())


def test_cmdline_update_error(sample_data1, sample_data2):

    from .test_cmdline import run_update_error

    run_update_error(
        "%s" % sample_data1.bucket,
        "%s" % sample_data2.bucket,
        _get_b2_info(),
    )


def test_cmdline_update_multiple(sample_data1, sample_data2):

    from .test_cmdline import run_update_multiple

    run_update_multiple(
        "%s" % sample_data1.bucket,
        "%s" % sample_data2.bucket,
        _get_b2_info(),
    )


def test_cmdline_update_cmdline(sample_data1):

    from .test_cmdline import run_update_cmdline

    run_update_cmdline("%s" % sample_data1.bucket, [])
