# PyAlgoTrade
# 
# Copyright 2012 Gabriel Martin Becedillas Ruiz
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

import unittest

from pyalgotrade import barfeed
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.barfeed import sqlitefeed
from pyalgotrade import marketsession
from pyalgotrade import strategy
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross
import common

class NikkeiSpyStrategy(strategy.Strategy):
	def __init__(self, feed, smaPeriod):
		strategy.Strategy.__init__(self, feed)

		assert(smaPeriod > 3)
		self.__lead = "^n225"
		self.__lag = "spy"
		# Exit signal is more sensitive than entry.
		adjClose = feed[self.__lead].getAdjCloseDataSeries()
		self.__crossAbove = cross.CrossAbove(adjClose, ma.SMA(adjClose, smaPeriod))
		self.__crossBelow = cross.CrossAbove(adjClose, ma.SMA(adjClose, int(smaPeriod/2)))
		self.__pos = None

	def onEnterCanceled(self, position):
		assert(position == self.__pos)
		self.__pos = None

	def onExitOk(self, position):
		assert(position == self.__pos)
		self.__pos = None

	def __calculatePosSize(self):
		cash = self.getBroker().getCash()
		lastPrice = self.getFeed()[self.__lag][-1].getClose()
		ret =  cash / lastPrice
		return int(ret)

	def onBars(self, bars):
		if bars.getBar(self.__lead):
			if self.__crossAbove[-1] == 1 and self.__pos == None:
				shares = self.__calculatePosSize()
				if shares:
					self.__pos = self.enterLong(self.__lag, shares)
			elif self.__crossBelow[-1] == 1 and self.__pos != None:
				self.exitPosition(self.__pos)

class TestCase(unittest.TestCase):
	def __testDifferentTimezonesImpl(self, feed):
		self.assertTrue("^n225" in feed)
		self.assertTrue("spy" in feed)
		self.assertTrue("cacho" not in feed)
		strat = NikkeiSpyStrategy(feed, 34)
		strat.run()
		self.assertEqual(round(strat.getResult(), 2), 1125558.12)

	def testDifferentTimezones(self):
		# Market times in UTC:
		# - TSE: 0hs ~ 6hs
		# - US: 14:30hs ~ 21hs
		feed = yahoofeed.Feed()
		for year in [2010, 2011]:
			feed.addBarsFromCSV("^n225", common.get_data_file_path("nikkei-%d-yahoofinance.csv" % year), marketsession.TSE.getTimezone())
			feed.addBarsFromCSV("spy", common.get_data_file_path("spy-%d-yahoofinance.csv" % year), marketsession.USEquities.getTimezone())

		self.__testDifferentTimezonesImpl(feed)

	def testDifferentTimezones_DBFeed(self):
		feed = sqlitefeed.Feed(common.get_data_file_path("multiinstrument.sqlite"), barfeed.Frequency.DAY)
		feed.loadBars("^n225")
		feed.loadBars("spy")
		self.__testDifferentTimezonesImpl(feed)

	def testDifferentTimezones_DBFeed_LocalizedBars(self):
		feed = sqlitefeed.Feed(common.get_data_file_path("multiinstrument.sqlite"), barfeed.Frequency.DAY)
		feed.loadBars("^n225", marketsession.TSE.getTimezone())
		feed.loadBars("spy", marketsession.USEquities.getTimezone())
		self.__testDifferentTimezonesImpl(feed)

def getTestCases():
	ret = []
	ret.append(TestCase("testDifferentTimezones"))
	ret.append(TestCase("testDifferentTimezones_DBFeed"))
	ret.append(TestCase("testDifferentTimezones_DBFeed_LocalizedBars"))
	return ret


