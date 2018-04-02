#!/usr/bin/env python


'''Reporting infrastructure'''


import os
import six
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

		hostname (str): The string to use for hostname

    sender (str): The e-mail sender

    to (str): The e-mail receiver

  '''

  def __init__(self, subject, body, hostname, sender, to):

    # get information from package and host, put on header
    prefix = '[baker-%s@%s] ' % \
        (pkg_resources.require('baker')[0].version, hostname)

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


_INTERVALS = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', 3600),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
    )

def human_time(seconds, granularity=2):
  '''Returns a human readable time string like "1 day, 2 hours"'''

  result = []

  for name, count in _INTERVALS:
    value = seconds // count
    if value:
      seconds -= value * count
      if value == 1:
        name = name.rstrip('s')
      result.append("{} {}".format(value, name))
    else:
      # Add a blank if we're in the middle of other values
      if len(result) > 0:
        result.append(None)

  if not result:
    return '%.2f seconds' % seconds

  return ', '.join([x for x in result[:granularity] if x is not None])


class LogCapture(object):
  '''Captures messages for a particular logger from the python logging service

  Parameters:

    name (str): The name of the base logger to capture messages from

    level (int, Optional): The integer level to set the handler to

  '''


  def __init__(self, name, level=logging.DEBUG):

    self.logger = logging.getLogger(name)
    self.buffer = six.StringIO()
    self.handler = logging.StreamHandler(self.buffer)
    self.handler.setLevel(level)


  def __enter__(self):

    self.logger.addHandler(self.handler)
    return self.buffer


  def __exit__(self, et, ev, tb):

    self.logger.removeHandler(self.handler)
    self.handler.close()
    self.buffer.seek(0) #make it ready for readout
