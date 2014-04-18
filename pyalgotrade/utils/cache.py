__author__ = 'tiborkiss'

import collections
import functools


class BoundedOrderedDict(collections.OrderedDict):
    def __init__(self, *args, **kwds):
        self.maxlen = kwds.pop("maxlen", None)
        collections.OrderedDict.__init__(self, *args, **kwds)
        self._checklen()

    def __setitem__(self, key, value):
        collections.OrderedDict.__setitem__(self, key, value)
        self._checklen()

    def _checklen(self):
        if self.maxlen is not None:
            while len(self) > self.maxlen:
                self.popitem(last=False)


def memoize(func=None, maxlen=None):
    """ Fixed size cache decorator"""
    if func:
        cache = BoundedOrderedDict(maxlen=maxlen)
        @functools.wraps(func)
        def memo_target(*args):
            lookup_value = args
            if lookup_value not in cache:
                cache[lookup_value] = func(*args)
            return cache[lookup_value]
        return memo_target
    else:
        def memoize_factory(func):
            return memoize(func, maxlen=maxlen)
        return memoize_factory
