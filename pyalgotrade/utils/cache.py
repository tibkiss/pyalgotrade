__author__ = 'tiborkiss'

import logging
log = logging.getLogger(__name__)

import collections
import functools


class BoundedOrderedDict(collections.OrderedDict):
    def __init__(self, size, *args, **kwds):
        self.size = size
        collections.OrderedDict.__init__(self, *args, **kwds)
        self._checklen()
        log.debug('FixedCache size: %d' % size)

    def __setitem__(self, key, value):
        collections.OrderedDict.__setitem__(self, key, value)
        self._checklen()

    def _checklen(self):
        if self.size != 0:
            while len(self) > self.size:
                self.popitem(last=False)

class LRUCache(object):
    """
    LRU Cache based on a Python OrderedDict
    The OrderedDict is a dict that maintains a doubly linked list which saves the order
    that keys are inserted.  When a cache item is accessed, the item is popped
    and reinserted in the OrderedDict so that the recently used order is preserved.
    The internal OrderedDict is accessible as `self.data`
    OrderedDict references
    http://docs.python.org/library/collections.html#collections.OrderedDict
    http://hg.python.org/cpython/file/70274d53c1dd/Lib/collections.py
    """
    def __init__(self, size):
        self.size = size
        self.data = collections.OrderedDict()
        log.debug('LRU Cache size: %d' % size)

    def __getitem__(self, key):
        # pop and reinsert so that this item is now last
        value = self.data.pop(key)
        self.data[key] = value
        return value

    def __setitem__(self, key, value):
        if key in self.data:
            self.data.pop(key)
        elif self.size != 0 and len(self.data) == self.size:
            # cache full: delete the least recently used item (first item)
            self.data.popitem(last=False)
        self.data[key] = value

    def __contains__(self, item):
        return item in self.data

    def __str__(self):
        return "LRUCache (size={size}, length={length}) {data}".format(
                size=self.size, length=len(self.data), data=str(self.data))

    def lru(self):
        """
        Returns the least recently used item's (key, value) tuple
        """
        if len(self.data) == 0:
            return None
        key = self.data.iterkeys().next()
        return (key, self.data[key])

    def keys(self):
        """
        Returns the keys in the cache ordered from least recently used to
        most recently used
        """
        return self.data.keys()


def memoize(func=None, size=0, lru=False):
    """ Cache decorator"""
    if func:
        if lru:
            cache = LRUCache(int(size))
        else:
            # FIFO cache replacement policy
            cache = BoundedOrderedDict(int(size))
        @functools.wraps(func)
        def memo_target(*args):
            lookup_value = args
            if lookup_value not in cache:
                cache[lookup_value] = func(*args)
            return cache[lookup_value]
        return memo_target
    else:
        def memoize_factory(func):
            return memoize(func, size, lru)
        return memoize_factory
