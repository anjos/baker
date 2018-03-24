#!/usr/bin/env python


'''Reporting infrastructure'''


import os
import sys
import smtplib
import pkg_resources
import email.mime.text

import logging
logger = logging.getLogger(__name__)


class Email(object):
  '''An object representing a message to be sent to maintainers


  Parameters:

    subject (str): The e-mail subject

    body (str): The e-mail body

    sender (str): The e-mail sender

    to (str): The e-mail receiver

  '''

  def __init__(self, subject, body, hostname, sender, to):

    # get information from package and host, put on header
    prefix = '[backuper-%s@%s] ' % \
        (pkg_resources.require('popster')[0].version, hostname)

    self.subject = prefix + subject
    self.body = body
    self.sender = sender
    self.to = to

    # mime message setup
    self.msg = email.mime.text.MIMEText(self.body)
    self.msg['Subject'] = self.subject
    self.msg['From'] = self.sender
    self.msg['To'] = ', '.join(self.to)


  def send(self, server, port, username, password):

    server = smtplib.SMTP(server, port)
    server.ehlo()
    server.starttls()
    server.login(username, password)
    server.sendmail(self.sender, self.to, self.msg.as_bytes())
    server.close()


  def message(self):
    '''Returns a string representation of the message'''

    return self.msg.as_string()


def setup_logger(name, verbosity):
  '''Sets up the logging of a script


  Parameters:

    name (str): The name of the logger to setup

    verbosity (int): The verbosity level to operate with. A value of ``0``
      (zero) means only errors, ``1``, errors and warnings; ``2``, errors,
      warnings and informational messages and, finally, ``3``, all types of
      messages including debugging ones.

  '''

  logger = logging.getLogger(name)
  formatter = logging.Formatter("%(name)s@%(asctime)s -- %(levelname)s: " \
      "%(message)s")

  _warn_err = logging.StreamHandler(sys.stderr)
  _warn_err.setFormatter(formatter)
  _warn_err.setLevel(logging.WARNING)

  class _InfoFilter:
    def filter(self, record): return record.levelno <= logging.INFO
  _debug_info = logging.StreamHandler(sys.stdout)
  _debug_info.setFormatter(formatter)
  _debug_info.setLevel(logging.DEBUG)
  _debug_info.addFilter(_InfoFilter())

  logger.addHandler(_debug_info)
  logger.addHandler(_warn_err)


  logger.setLevel(logging.ERROR)
  if verbosity == 1: logger.setLevel(logging.WARNING)
  elif verbosity == 2: logger.setLevel(logging.INFO)
  elif verbosity >= 3: logger.setLevel(logging.DEBUG)

  return logger


class LoggingSaver(object):

  def __init__(self, logger):
    self.logger = logger
    self.buffer = StringIO()
    self.handler = logging.StreamHandler(self.buffer)

  def __enter__(self):
    self.logger.addHandler(self.handler)

  def __exit__(self, et, ev, tb):
    self.logger.removeHandler(self.handler)
    self.handler.close()
