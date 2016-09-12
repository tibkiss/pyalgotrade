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

from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross
import common

class SMACrossOverStrategy(strategy.Strategy):
    def __init__(self, feed, fastSMA, slowSMA):
        strategy.Strategy.__init__(self, feed, 1000)
        ds = feed["orcl"].getCloseDataSeries()
        fastSMADS = ma.SMA(ds, fastSMA)
        slowSMADS = ma.SMA(ds, slowSMA)
        self.__crossAbove = cross.CrossAbove(fastSMADS, slowSMADS)
        self.__crossBelow = cross.CrossBelow(fastSMADS, slowSMADS)
        self.__longPos = None
        self.__shortPos = None
        self.__finalValue = None

    def enterLongPosition(self, bars):
        raise Exception("Not implemented")

    def enterShortPosition(self, bars):
        raise Exception("Not implemented")

    def exitLongPosition(self, bars, position):
        raise Exception("Not implemented")

    def exitShortPosition(self, bars, position):
        raise Exception("Not implemented")

    def getFinalValue(self):
        return self.__finalValue

    def printDebug(self, *args):
        args = [str(arg) for arg in args]
        # print " ".join(args)

    def onEnterOk(self, position):
        self.printDebug("enterOk: ", self.getCurrentDateTime(), position.getEntryOrder().getExecutionInfo().getPrice(), position)

    def onEnterCanceled(self, position):
        self.printDebug("enterCanceled: ", self.getCurrentDateTime(), position)
        if position == self.__longPos:
            self.__longPos = None
        elif position == self.__shortPos:
            self.__shortPos = None
        else:
            assert(False)

    def onExitOk(self, position):
        self.printDebug("exitOk: ", self.getCurrentDateTime(), position.getExitOrder().getExecutionInfo().getPrice(), position)
        if position == self.__longPos:
            self.__longPos = None
        elif position == self.__shortPos:
            self.__shortPos = None
        else:
            assert(False)

    def onExitCanceled(self, position):
        self.printDebug("exitCanceled: ", self.getCurrentDateTime(), position, ". Resubmitting as a Market order.")
        # If the exit was canceled, re-submit it.
        self.exitPosition(position)

    def onBars(self, bars):
        bar = bars.getBar("orcl")
        self.printDebug("%s: O=%s H=%s L=%s C=%s" % (bar.getDateTime(), bar.getOpen(), bar.getHigh(), bar.getLow(), bar.getClose()))

        # Wait for enough bars to be available.
        if self.__crossAbove[-1] is None or self.__crossBelow[-1] is None:
            return

        if self.__crossAbove[-1] == 1:
            if self.__shortPos:
                self.exitShortPosition(bars, self.__shortPos)
            assert(self.__longPos == None)
            self.__longPos = self.enterLongPosition(bars)
        elif self.__crossBelow[-1] == 1:
            if self.__longPos:
                self.exitLongPosition(bars, self.__longPos)
            assert(self.__shortPos == None)
            self.__shortPos = self.enterShortPosition(bars)

    def onFinish(self, bars):
        self.__finalValue = self.getBroker().getValue(bars)

class MarketOrderStrategy(SMACrossOverStrategy):
    def enterLongPosition(self, bars):
        return self.enterLong("orcl", 10)

    def enterShortPosition(self, bars):
        return self.enterShort("orcl", 10)

    def exitLongPosition(self, bars, position):
        self.exitPosition(position)

    def exitShortPosition(self, bars, position):
        self.exitPosition(position)

class LimitOrderStrategy(SMACrossOverStrategy):
    def __getMiddlePrice(self, bars):
        bar = bars.getBar("orcl")
        ret = bar.getLow() + (bar.getHigh() - bar.getLow()) / 2.0
        ret = round(ret, 2)
        return ret

    def enterLongPosition(self, bars):
        price = self.__getMiddlePrice(bars)
        ret = self.enterLongLimit("orcl", price, 10)
        self.printDebug("enterLong:", self.getCurrentDateTime(), price, ret)
        return ret

    def enterShortPosition(self, bars):
        price = self.__getMiddlePrice(bars)
        ret = self.enterShortLimit("orcl", price, 10)
        self.printDebug("enterShort:", self.getCurrentDateTime(), price, ret)
        return ret

    def exitLongPosition(self, bars, position):
        price = self.__getMiddlePrice(bars)
        self.printDebug("exitLong:", self.getCurrentDateTime(), price, position)
        self.exitPosition(position, price)

    def exitShortPosition(self, bars, position):
        price = self.__getMiddlePrice(bars)
        self.printDebug("exitShort:", self.getCurrentDateTime(), price, position)
        self.exitPosition(position, price)

class TestSMACrossOver(unittest.TestCase):
    def __test(self, strategyClass, finalValue):
        feed = yahoofeed.Feed()
        feed.addBarsFromCSV("orcl", common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        myStrategy = strategyClass(feed, 10, 25)
        myStrategy.run()
        myStrategy.printDebug("Final result:", round(myStrategy.getFinalValue(), 2))
        assert round(myStrategy.getFinalValue(), 2) == finalValue

    def testWithMarketOrder(self):
        # This is the exact same result that we get using NinjaTrader.
        self.__test(MarketOrderStrategy, 1000 - 22.7)

    def testWithLimitOrder(self):
        # The result is different than the one we get using NinjaTrader. NinjaTrader processes Limit orders in a different way.
        self.__test(LimitOrderStrategy, 1000 + 32.7)

def getTestCases():
    ret = []
    ret.append(TestSMACrossOver("testWithMarketOrder"))
    ret.append(TestSMACrossOver("testWithLimitOrder"))
    return ret
