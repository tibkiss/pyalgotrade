# PyAlgoTrade
#
# Copyright 2011 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

import pytest
import unittest
import datetime

from pyalgotrade import dataseries
from pyalgotrade import bar

class TestSequenceDataSeries(unittest.TestCase):
    def testEmpty(self):
        ds = dataseries.SequenceDataSeries([])
        assert ds.getFirstValidPos() == 0
        assert ds.getLength() == 0
        with self.assertRaises(IndexError):
            ds[-1]
        with self.assertRaises(IndexError):
            ds[-2]
        with self.assertRaises(IndexError):
            ds[0]
        with self.assertRaises(IndexError):
            ds[1]

    def testNonEmpty(self):
        ds = dataseries.SequenceDataSeries(range(10))
        assert ds.getFirstValidPos() == 0
        assert ds.getLength() == 10
        assert ds[-1] == 9
        assert ds[-2] == 8
        assert ds[0] == 0
        assert ds[1] == 1

        assert ds[-1:] == [9]
        assert ds[-2:] == [8, 9]
        assert ds[-2:-1] == [8]
        assert ds[-3:-1] == [7, 8]

        assert ds.getValuesAbsolute(1, 3) == [1, 2, 3]
        assert ds.getValuesAbsolute(9, 9) == [9]
        assert ds.getValuesAbsolute(9, 10) == None
        assert ds.getValuesAbsolute(9, 10, True) == [9, None]

    def testSeqLikeOps(self):
        seq = range(10)
        ds = dataseries.SequenceDataSeries(seq)

        # Test length and every item.
        self.assertEqual(len(ds), len(seq))
        for i in xrange(len(seq)):
            self.assertEqual(ds[i], seq[i])

        # Test negative indices
        self.assertEqual(ds[-1], seq[-1])
        self.assertEqual(ds[-2], seq[-2])
        self.assertEqual(ds[-9], seq[-9])

        # Test slices
        sl = slice(0,1,2)
        self.assertEqual(ds[sl], seq[sl])
        sl = slice(0,9,2)
        self.assertEqual(ds[sl], seq[sl])
        sl = slice(0,-1,1)
        self.assertEqual(ds[sl], seq[sl])

        for i in xrange(-100, 100):
            self.assertEqual(ds[i:], seq[i:])

        for step in xrange(1, 10):
            for i in xrange(-100, 100):
                self.assertEqual(ds[i::step], seq[i::step])

class TestBarDataSeries(unittest.TestCase):
    def testEmpty(self):
        ds = dataseries.BarDataSeries()
        with self.assertRaises(IndexError):
            ds[-1]
        with self.assertRaises(IndexError):
            ds[0]
        with self.assertRaises(IndexError):
            ds[1000]

    # This testcase is disabled as IB live feed has no strict bar ordering
    # def testAppendInvalidDatetime(self):
    #     ds = dataseries.BarDataSeries()
    #     for i in range(10):
    #         now = datetime.datetime.now() + datetime.timedelta(seconds=i)
    #         ds.appendValue( bar.Bar(now, 0, 0, 0, 0, 0, 0) )
    #         # Adding the same datetime twice should fail
    #         self.assertRaises(Exception, ds.appendValue, bar.Bar(now, 0, 0, 0, 0, 0, 0))
    #         # Adding a previous datetime should fail
    #         self.assertRaises(Exception, ds.appendValue, bar.Bar(now - datetime.timedelta(seconds=i), 0, 0, 0, 0, 0, 0))

    def testNonEmpty(self):
        ds = dataseries.BarDataSeries()
        for i in range(10):
            ds.appendValue( bar.Bar(datetime.datetime.now() + datetime.timedelta(seconds=i), 0, 0, 0, 0, 0, 0) )

        for i in range(0, 10):
            assert ds[i].getOpen() == 0

    def __testGetValue(self, ds, itemCount, value):
        for i in range(0, itemCount):
            assert ds[i] == value

    def testNestedDataSeries(self):
        ds = dataseries.BarDataSeries()
        for i in range(10):
            ds.appendValue( bar.Bar(datetime.datetime.now() + datetime.timedelta(seconds=i), 2, 4, 1, 3, 10, 3) )

        self.__testGetValue(ds.getOpenDataSeries(), 10, 2)
        self.__testGetValue(ds.getCloseDataSeries(), 10, 3)
        self.__testGetValue(ds.getHighDataSeries(), 10, 4)
        self.__testGetValue(ds.getLowDataSeries(), 10, 1)
        self.__testGetValue(ds.getVolumeDataSeries(), 10, 10)
        self.__testGetValue(ds.getAdjCloseDataSeries(), 10, 3)

    def testSeqLikeOps(self):
        seq = []
        ds = dataseries.BarDataSeries()
        for i in range(10):
            bar_ = bar.Bar(datetime.datetime.now() + datetime.timedelta(seconds=i), 2, 4, 1, 3, 10, 3)
            ds.appendValue(bar_)
            seq.append(bar_)

        self.assertEqual(ds[-1], seq[-1])
        self.assertEqual(ds[-2], seq[-2])
        self.assertEqual(ds[0], seq[0])
        self.assertEqual(ds[1], seq[1])
        self.assertEqual(ds[-2:][-1], seq[-2:][-1])

    def testDateTimes(self):
        ds = dataseries.BarDataSeries()
        firstDt = datetime.datetime.now()
        for i in range(10):
            ds.appendValue( bar.Bar(firstDt + datetime.timedelta(seconds=i), 2, 4, 1, 3, 10, 3) )

        for i in range(10):
            self.assertEqual(ds[i].getDateTime(), ds.getDateTimes()[i])
            self.assertEqual(ds.getDateTimes()[i], firstDt + datetime.timedelta(seconds=i))

class TestDateAlignedDataSeries(unittest.TestCase):
    def testNotAligned(self):
        size = 20
        ds1 = dataseries.SequenceDataSeries()
        ds2 = dataseries.SequenceDataSeries()

        now = datetime.datetime.now()
        for i in range(size):
            if i % 2 == 0:
                ds1.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)
            else:
                ds2.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)

        self.assertEqual(len(ds1), len(ds2))

        ads1, ads2 = dataseries.datetime_aligned(ds1, ds2)
        for ads in [ads1, ads2]:
            self.assertEqual(ads.getLength(), 0)
            self.assertEqual(ads.getFirstValidPos(), 0)
            self.assertEqual(ads.getValueAbsolute(0), None)
            self.assertEqual(ads.getDateTimes(), [])

    def testFullyAligned(self):
        size = 20
        ds1 = dataseries.SequenceDataSeries()
        ds2 = dataseries.SequenceDataSeries()

        now = datetime.datetime.now()
        for i in range(size):
            ds1.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)
            ds2.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)

        self.assertEqual(len(ds1), len(ds2))

        ads1, ads2 = dataseries.datetime_aligned(ds1, ds2)
        for ads in [ads1, ads2]:
            self.assertEqual(ads.getLength(), size)
            self.assertEqual(ads.getFirstValidPos(), 0)
            for i in range(size):
                self.assertEqual(ads.getValueAbsolute(i), i)
                self.assertEqual(ads.getDateTimes()[i], now + datetime.timedelta(seconds=i))

    def testPartiallyAligned(self):
        size = 20
        ds1 = dataseries.SequenceDataSeries()
        ds2 = dataseries.SequenceDataSeries()
        commonDateTimes = []

        now = datetime.datetime.now()
        for i in range(size):
            if i % 3 == 0:
                commonDateTimes.append(now + datetime.timedelta(seconds=i))
                ds1.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)
                ds2.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)
            elif i % 2 == 0:
                ds1.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)
            else:
                ds2.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)

        ads1, ads2 = dataseries.datetime_aligned(ds1, ds2)

        self.assertEqual(ads1.getLength(), ads2.getLength())
        self.assertEqual(ads1[:], ads2[:])
        self.assertEqual(ads1.getDateTimes(), commonDateTimes)
        self.assertEqual(ads2.getDateTimes(), commonDateTimes)

    def testIncremental(self):
        size = 20
        ds1 = dataseries.SequenceDataSeries()
        ds2 = dataseries.SequenceDataSeries()
        ads1, ads2 = dataseries.datetime_aligned(ds1, ds2)

        now = datetime.datetime.now()
        for i in range(size):
            ds1.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)
            ds2.appendValueWithDatetime(now + datetime.timedelta(seconds=i), i)
            self.assertEqual(ads1.getLength(), ads2.getLength())
            self.assertEqual(ads1[:], ads2[:])
            self.assertEqual(ads1.getDateTimes()[:], ads2.getDateTimes()[:])

