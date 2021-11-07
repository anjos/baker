#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""Tests for the QNAP Container Station API"""


from . import qnap


session = None


def setup():

    global session
    session = qnap.login()


def teardown():

    qnap.logout()


def test_system():

    info = qnap.system(session)
    assert info["status"] == "running"
    assert info["needRestart"] == False


def test_get_containers():

    info = qnap.get_containers(session)
    assert isinstance(info, list)
