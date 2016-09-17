# PyAlgoTrade
#
# Copyright 2011 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
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

import pytz

import common

from pyalgotrade.barfeed import csvfeed
from pyalgotrade.providers.interactivebrokers.ibfeed import CSVFeed, LiveFeed, RowParser
from pyalgotrade.providers.interactivebrokers.ibconnection import Connection
from pyalgotrade.providers.interactivebrokers.ibbar import Bar
from ib_testeclientsocket import TestEClientSocket

class BarFeedEventHandler_TestLoadOrder:
    def __init__(self, testcase, barFeed, instrument):
        self.__testcase = testcase
        self.__count = 0
        self.__prevDateTime = None
        self.__barFeed = barFeed
        self.__instrument = instrument

    def onBars(self, bars):
        self.__count += 1
        dateTime = bars.getBar(self.__instrument).getDateTime()
        if self.__prevDateTime != None:
            # Check that bars are loaded in order
            self.__testcase.assertTrue(self.__prevDateTime < dateTime)
            # Check that the last value in the dataseries match the current datetime.
            self.__testcase.assertTrue(self.__barFeed.getDataSeries().getValue().getDateTime() == dateTime)
        self.__prevDateTime = dateTime

    def getEventCount(self):
        return self.__count

class BarFeedEventHandler_TestFilterRange:
    def __init__(self, testcase, instrument, fromDate, toDate):
        self.__testcase = testcase
        self.__count = 0
        self.__instrument = instrument
        self.__fromDate = fromDate
        self.__toDate = toDate

    def onBars(self, bars):
        self.__count += 1

        if self.__fromDate != None:
            self.__testcase.assertTrue(bars.getBar(self.__instrument).getDateTime() >= self.__fromDate)
        if self.__toDate != None:
            self.__testcase.assertTrue(bars.getBar(self.__instrument).getDateTime() <= self.__toDate)

    def getEventCount(self):
        return self.__count

class IBCSVFeedTestCase(unittest.TestCase):
    TestInstrument = "spy"

    def __parseDate(self, date):
        parser = RowParser()
        row = {"Date":date, "Close":0, "Open":0 , "High":0 , "Low":0 , "Volume":0 , "TradeCount":0 , "VWAP":0 , "HasGap": "False"}
        return parser.parseBar(row).getDateTime()

    def testParseDate_1(self):
        date = self.__parseDate("2012-06-29 01:55:00")
        assert date.day == 29
        assert date.month == 06
        assert date.year == 2012

        assert date.hour == 01
        assert date.minute == 55
        assert date.second == 00

    def testDateCompare(self):
        assert self.__parseDate("2012-06-29 00:55:00") != self.__parseDate("2012-06-29 01:55:00")
        assert self.__parseDate("2011-06-29 00:55:00") < self.__parseDate("2012-06-29 01:55:00")
        assert self.__parseDate("2012-06-29 00:55:00") < self.__parseDate("2012-06-29 01:55:00")

    def testCSVFeedLoadOrder(self):
        barFeed = CSVFeed()
        barFeed.addBarsFromCSV(IBCSVFeedTestCase.TestInstrument, common.get_data_file_path("ib-spy-5min-20120627.csv"))
        barFeed.addBarsFromCSV(IBCSVFeedTestCase.TestInstrument, common.get_data_file_path("ib-spy-5min-20120628.csv"))
        barFeed.addBarsFromCSV(IBCSVFeedTestCase.TestInstrument, common.get_data_file_path("ib-spy-5min-20120629.csv"))

        handler = BarFeedEventHandler_TestLoadOrder(self, barFeed, IBCSVFeedTestCase.TestInstrument)
        barFeed.getNewBarsEvent().subscribe(handler.onBars)
        while not barFeed.stopDispatching():
            barFeed.dispatch()
        assert handler.getEventCount() > 0

    def __testFilteredRangeImpl(self, fromDate, toDate):
        barFeed = CSVFeed()
        barFeed.setBarFilter(csvfeed.DateRangeFilter(fromDate, toDate))
        barFeed.addBarsFromCSV(IBCSVFeedTestCase.TestInstrument, common.get_data_file_path("ib-spy-5min-20120627.csv"))
        barFeed.addBarsFromCSV(IBCSVFeedTestCase.TestInstrument, common.get_data_file_path("ib-spy-5min-20120628.csv"))
        barFeed.addBarsFromCSV(IBCSVFeedTestCase.TestInstrument, common.get_data_file_path("ib-spy-5min-20120629.csv"))

        # Dispatch and handle events.
        handler = BarFeedEventHandler_TestFilterRange(self, IBCSVFeedTestCase.TestInstrument, fromDate, toDate)
        barFeed.getNewBarsEvent().subscribe(handler.onBars)
        while not barFeed.stopDispatching():
            barFeed.dispatch()
        assert handler.getEventCount() > 0

    def testFilteredRangeFrom(self):
        self.__testFilteredRangeImpl(datetime.datetime(2012, 06, 28, 00, 00, tzinfo=pytz.UTC), None)

    def testFilteredRangeTo(self):
        self.__testFilteredRangeImpl(None, datetime.datetime(2012, 06, 29, 23, 55, tzinfo=pytz.UTC))

    def testFilteredRangeFromTo(self):
        self.__testFilteredRangeImpl(datetime.datetime(2000, 1, 1, 00, 00, tzinfo=pytz.UTC),
                                     datetime.datetime(2020, 12, 31, 23, 55, tzinfo=pytz.UTC))

class IBLiveFeedTestCase(unittest.TestCase):
    TestInstrument = "spy"

    def setUp(self):
        self.__testTWS = TestEClientSocket(self)
        self.__conn = Connection(eClientSocket=self.__testTWS)
        self.__feed = LiveFeed(self.__conn)

    def testSubscription(self):
        instrument1 = 'XXX'
        instrument2 = 'YYY'
        instrument3 = 'ZZZ'

        for useRTH in (0, 1):
            # Check if multiple instruments are supported
            self.__feed.subscribeRealtimeBars(instrument1, useRTH)
            self.assertIn(instrument1, self.__feed.getRegisteredInstruments())
            self.__feed.subscribeRealtimeBars(instrument2, useRTH)
            self.assertIn(instrument1, self.__feed.getRegisteredInstruments())
            self.assertIn(instrument2, self.__feed.getRegisteredInstruments())

            # XXX: There is no way to unsubscribe from a BarFeed yet
            # self.__feed.unsubscribeRealtimeBars(instrument1)
            # self.assertNotIn(instrument1, self.__feed.getRegisteredInstruments())
            # self.assertIn(instrument2, self.__feed.getRegisteredInstruments())
            # self.__feed.unsubscribeRealtimeBars(instrument2)
            # self.assertNotIn(instrument1, self.__feed.getRegisteredInstruments())
            # self.assertNotIn(instrument2, self.__feed.getRegisteredInstruments())

            self.__feed.subscribeRealtimeBars(instrument3, useRTH)

            # Test if the realtime bar request reached tws
            self.assertEqual(instrument3, self.__testTWS.realtimeContract.m_symbol)
            self.assertEqual("STK", self.__testTWS.realtimeContract.m_secType)
            self.assertEqual("SMART", self.__testTWS.realtimeContract.m_exchange)
            self.assertEqual("USD", self.__testTWS.realtimeContract.m_currency)
            self.assertEqual(5, self.__testTWS.realtimeBarSize)
            self.assertEqual("TRADES", self.__testTWS.realtimeWhatToShow)
            self.assertEqual(useRTH, self.__testTWS.realtimeUseRTH)

            self.__feed.unsubscribeRealtimeBars(instrument3)

    @pytest.mark.xfail(strict=True)
    def testRealtimeBars(self):
        # Call onRealtimeBar with the instrument & bar tuple.
        # The result should appear in the consecutive fetchNextBars call
        instrument1 = 'XXX'
        instrument2 = 'YYY'
        instrument3 = 'ZZZ'
        instrument4 = 'QQQ'
        bar1 = Bar(datetime.datetime(2012, 8, 9, 12, 20, 00), open_=1.31, high=2.51, low=0.91, close=2.11,
                                                           volume=11, vwap=14.11, tradeCount=51)
        bar2 = Bar(datetime.datetime(2012, 8, 9, 12, 20, 00), open_=1.32, high=2.52, low=0.92, close=2.12,
                                                           volume=12, vwap=14.12, tradeCount=52)
        bar3 = Bar(datetime.datetime(2012, 8, 9, 12, 20, 05), open_=1.43, high=2.53, low=0.93, close=2.13,
                                                           volume=13, vwap=14.13, tradeCount=53)
        bar4 = Bar(datetime.datetime(2012, 8, 9, 12, 20, 10), open_=1.44, high=2.54, low=0.94, close=2.14,
                                                           volume=11, vwap=14.14, tradeCount=54)

        # Add bar1 and test the presence using fetchNextBars
        # Bar1 should not be present until the timestamp is increased
        # on the nex onRealtimeBar call
        self.__feed.onIBBar((instrument1, bar1))

        # Add bar2 with the same timestamp. No bars should be present
        self.__feed.onIBBar((instrument2, bar2))

        # Add bar3 with the next timestamp to trigger transfer between onRealtimeBar and fetchNextBars
        self.__feed.onIBBar((instrument3, bar3))
        bars = self.__feed.fetchNextBars()
        self.assertIn(instrument1, bars.keys())
        self.assertIn(instrument2, bars.keys())
        self.assertNotIn(instrument3, bars.keys())
        self.assertNotIn(instrument4, bars.keys())
        self.assertEqual(bars[instrument1], bar1)
        self.assertEqual(bars[instrument2], bar2)

        # Add bar4, only bar3 should return
        self.__feed.onIBBar((instrument4, bar4))
        bars = self.__feed.fetchNextBars()
        self.assertNotIn(instrument1, bars.keys())
        self.assertNotIn(instrument2, bars.keys())
        self.assertIn(instrument3, bars.keys())
        self.assertNotIn(instrument4, bars.keys())
        self.assertEqual(bars[instrument3], bar3)


def getTestCases():
    ret = []
    ret.append(IBCSVFeedTestCase("testParseDate_1"))
    ret.append(IBCSVFeedTestCase("testDateCompare"))
    ret.append(IBCSVFeedTestCase("testCSVFeedLoadOrder"))
    ret.append(IBCSVFeedTestCase("testFilteredRangeFrom"))
    ret.append(IBCSVFeedTestCase("testFilteredRangeTo"))
    ret.append(IBCSVFeedTestCase("testFilteredRangeFromTo"))
    ret.append(IBLiveFeedTestCase("testSubscription"))
    ret.append(IBLiveFeedTestCase("testRealtimeBars"))
    return ret


# vim: noet:ci:pi:sts=0:sw=4:ts=4
