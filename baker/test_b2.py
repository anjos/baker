#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for b2 infrastructure"""


import os
import uuid
import nose.tools
import pkg_resources
import tempfile
import logging

logger = logging.getLogger(__name__)

from . import b2
from . import restic


TEST_BUCKET_NAME = "baker-test-" + str(uuid.uuid4())[:8]
TEST_BUCKET_NAME2 = "baker-test-" + str(uuid.uuid4())[:8]
SAMPLE_DIR1 = pkg_resources.resource_filename(
    __name__, os.path.join("data", "dir1")
)
SAMPLE_DIR2 = pkg_resources.resource_filename(
    __name__, os.path.join("data", "dir2")
)


def setup():
    """Sets up the module infrastructure"""

    account_id, account_key = b2.setup()

    # Creates test buckets with a given known prefix (and a random bit)
    b2.create_bucket(TEST_BUCKET_NAME)
    b2.create_bucket(TEST_BUCKET_NAME2)


def teardown():

    b2.remove_bucket(TEST_BUCKET_NAME)
    b2.remove_bucket(TEST_BUCKET_NAME2)


def test_list_buckets():

    output = b2.list_buckets()
    assert TEST_BUCKET_NAME in output


def test_get_bucket():

    output = b2.get_bucket(TEST_BUCKET_NAME)
    assert "totalSize" in output


def test_list_bucket_contents():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)

    # Syncs our test directory with the bucket
    b2.sync(TEST_BUCKET_NAME, SAMPLE_DIR1)

    output = b2.bucket_contents(TEST_BUCKET_NAME)
    assert "example.txt" in output


def test_restic_init():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)
    repo = "b2:%s" % TEST_BUCKET_NAME

    with tempfile.TemporaryDirectory() as cache:
        out = restic.init(repo, [], "password", cache)

    messages = out.split("\n")[:-1]  # removes last end-of-line
    nose.tools.eq_(len(messages), 5)
    assert messages[0].startswith("created restic repository")
    assert messages[0].endswith(TEST_BUCKET_NAME)
    assert "config" in b2.bucket_contents(TEST_BUCKET_NAME)


def test_restic_backup():

    b2.empty_bucket(TEST_BUCKET_NAME)
    repo = "b2:%s" % TEST_BUCKET_NAME

    with tempfile.TemporaryDirectory() as cache:
        restic.init(repo, [], "password", cache)
        out = restic.backup(
            SAMPLE_DIR1, repo, [], "hostname", [], "password", cache
        )

    messages = out.split("\n")[:-1]  # removes last end-of-line
    nose.tools.eq_(len(messages), 8)
    assert messages[0].startswith("created new cache in")
    assert messages[0].endswith(cache)
    assert messages[1] == ""
    assert messages[-2].startswith("processed")
    assert messages[-1].startswith("snapshot")
    assert messages[-1].endswith("saved")


def test_restic_check():

    b2.empty_bucket(TEST_BUCKET_NAME)
    repo = "b2:%s" % TEST_BUCKET_NAME

    with tempfile.TemporaryDirectory() as cache:
        restic.init(repo, [], "password", cache)
        restic.backup(SAMPLE_DIR1, repo, [], "hostname", [], "password", cache)
        out = restic.check(repo, [], True, "password", cache)

    messages = out.split("\n")[:-1]  # removes last end-of-line
    nose.tools.eq_(len(messages), 7)
    assert messages[0].startswith("using temporary cache in %s" % cache)
    assert messages[1].startswith("created new cache in %s" % cache)
    nose.tools.eq_(messages[2], "create exclusive lock for repository")
    nose.tools.eq_(messages[3], "load indexes")
    nose.tools.eq_(messages[-1], "no errors were found")


def test_restic_snapshots():

    b2.empty_bucket(TEST_BUCKET_NAME)
    repo = "b2:%s" % TEST_BUCKET_NAME

    with tempfile.TemporaryDirectory() as cache:
        restic.init(repo, [], "password", cache)
        restic.backup(SAMPLE_DIR1, repo, [], "hostname", [], "password", cache)
        restic.backup(SAMPLE_DIR1, repo, [], "hostname", [], "password", cache)
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
    nose.tools.eq_(len(data), 2)
    nose.tools.eq_(data[0]["paths"], [SAMPLE_DIR1])
    nose.tools.eq_(data[0]["hostname"], "hostname")
    nose.tools.eq_(data[1]["paths"], [SAMPLE_DIR1])
    nose.tools.eq_(data[1]["hostname"], "hostname")


def test_restic_forget():

    b2.empty_bucket(TEST_BUCKET_NAME)
    repo = "b2:%s" % TEST_BUCKET_NAME

    with tempfile.TemporaryDirectory() as cache:
        restic.init(repo, [], "password", cache)
        restic.backup(SAMPLE_DIR1, repo, [], "hostname", [], "password", cache)
        data1 = restic.snapshots(
            repo, ["--json"], "hostname", "password", cache
        )
        restic.backup(SAMPLE_DIR1, repo, [], "hostname", [], "password", cache)
        restic.forget(
            repo, [], "hostname", True, {"last": 1}, "password", cache
        )
        data2 = restic.snapshots(
            repo, ["--json"], "hostname", "password", cache
        )

    # there are 2 backups which are nearly identical
    nose.tools.eq_(len(data2), 1)
    nose.tools.eq_(data2[0]["parent"], data1[0]["id"])
    assert data2[0]["id"] != data1[0]["id"]


def _get_b2_info():

    info = b2.get_account_info()
    return {"id": info["accountId"], "key": info["applicationKey"]}


def test_cmdline_init():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)

    # Retrieve credentials
    from .test_cmdline import run_init

    run_init("%s" % TEST_BUCKET_NAME, _get_b2_info())


def test_cmdline_init_error():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)

    from .test_cmdline import run_init_error

    run_init_error("%s" % TEST_BUCKET_NAME, _get_b2_info())


def test_cmdline_init_multiple():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)
    b2.empty_bucket(TEST_BUCKET_NAME2)

    from .test_cmdline import run_init_multiple

    run_init_multiple(
        "%s" % TEST_BUCKET_NAME, "%s" % TEST_BUCKET_NAME2, _get_b2_info()
    )


def test_cmdline_init_cmdline():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)

    from .test_cmdline import run_init_cmdline

    run_init_cmdline("%s" % TEST_BUCKET_NAME, [])


def test_cmdline_update():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)

    from .test_cmdline import run_update

    run_update("%s" % TEST_BUCKET_NAME, _get_b2_info())


def test_cmdline_update_recover():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)

    from .test_cmdline import run_update_recover

    run_update_recover("%s" % TEST_BUCKET_NAME, _get_b2_info())


def test_cmdline_update_error():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)
    b2.empty_bucket(TEST_BUCKET_NAME2)

    from .test_cmdline import run_update_error

    run_update_error(
        "%s" % TEST_BUCKET_NAME, "%s" % TEST_BUCKET_NAME2, _get_b2_info()
    )


def test_cmdline_update_multiple():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)
    b2.empty_bucket(TEST_BUCKET_NAME2)

    from .test_cmdline import run_update_multiple

    run_update_multiple(
        "%s" % TEST_BUCKET_NAME, "%s" % TEST_BUCKET_NAME2, _get_b2_info()
    )


def test_cmdline_update_cmdline():

    # Cleans-up bucket before starting
    b2.empty_bucket(TEST_BUCKET_NAME)

    from .test_cmdline import run_update_cmdline

    run_update_cmdline("%s" % TEST_BUCKET_NAME, [])
