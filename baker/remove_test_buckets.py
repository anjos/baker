#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''Removes all test buckets from my B2 account'''


def main():
  from . import b2
  buckets = b2.list_buckets()
  count = 0
  delete_keys = []
  for k, v in buckets.items():
    if k.startswith('baker-test-'):
      count += 1
      print('Removing test bucket "%s"...' % k)
      d = b2.remove_bucket(k)
      print('Removed bucket "%(bucketName)s" (id: %(bucketId)s)' % d)
      delete_keys.append(k)

  for k in delete_keys: del buckets[k]

  print('Only these buckets are now available:')
  for k in buckets.keys(): print('  * %s' % k)
