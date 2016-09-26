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

import pytest
import unittest

from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.barfeed import csvfeed
from pyalgotrade.stratanalyzer import returns
from pyalgotrade import broker

import strategy_test
import common


class PosTrackerTestCase(unittest.TestCase):
    invalid_price = 5000

    def testBuyAndSellBreakEvenWithCommission(self):
        posTracker = returns.PositionTracker()
        posTracker.buy(1, 10, 0.01)
        posTracker.sell(1, 10.02, 0.01)
        assert posTracker.getCost() == 10
        # We need to round here or else the testcase fails since the value returned is not exactly 0.<
        # The same issue can be reproduced with this piece of code:
        # a = 10.02 - 10
        # b = 0.02
        # print a - b
        # print a - b == 0
        assert round(posTracker.getNetProfit(PosTrackerTestCase.invalid_price), 2) == 0.0
        assert round(posTracker.getReturn(PosTrackerTestCase.invalid_price), 2) == 0.0

    def testBuyAndSellBreakEven(self):
        posTracker = returns.PositionTracker()
        posTracker.buy(1, 10)
        posTracker.sell(1, 10)
        assert posTracker.getCost() == 10
        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price) == 0
        assert posTracker.getReturn(PosTrackerTestCase.invalid_price) == 0

    def testBuyAndSellWin(self):
        posTracker = returns.PositionTracker()
        posTracker.buy(1, 10)
        posTracker.sell(1, 11)
        assert posTracker.getCost() == 10
        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price) == 1
        assert posTracker.getReturn(PosTrackerTestCase.invalid_price) == 0.1

    def testBuyAndSellMultipleEvals(self):
        posTracker = returns.PositionTracker()
        posTracker.buy(2, 10)
        assert posTracker.getCost() == 20
        assert posTracker.getNetProfit(10) == 0
        assert posTracker.getReturn(10) == 0

        assert posTracker.getNetProfit(11) == 2
        assert posTracker.getReturn(11) == 0.1

        assert posTracker.getNetProfit(20) == 20
        assert posTracker.getReturn(20) == 1

        posTracker.sell(1, 11)
        assert posTracker.getCost() == 20
        assert posTracker.getNetProfit(11) == 2
        assert posTracker.getReturn(11) == 0.1

        posTracker.sell(1, 10)
        assert posTracker.getCost() == 20
        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price) == 1
        assert posTracker.getReturn(11) == 0.05

    def testSellAndBuyWin(self):
        posTracker = returns.PositionTracker()
        posTracker.sell(1, 11)
        posTracker.buy(1, 10)
        assert posTracker.getCost() == 11
        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price) == 1
        assert round(posTracker.getReturn(PosTrackerTestCase.invalid_price), 4) == round(0.090909091, 4)

    def testSellAndBuyMultipleEvals(self):
        posTracker = returns.PositionTracker()
        posTracker.sell(2, 11)
        assert posTracker.getCost() == 22
        assert posTracker.getNetProfit(11) == 0
        assert posTracker.getReturn(11) == 0

        posTracker.buy(1, 10)
        assert posTracker.getCost() == 22
        assert posTracker.getNetProfit(11) == 1
        assert round(posTracker.getReturn(11), 4) == round(0.045454545, 4)

        posTracker.buy(1, 10)
        assert posTracker.getCost() == 22
        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price) == 2
        assert round(posTracker.getReturn(PosTrackerTestCase.invalid_price), 4) == round(0.090909091, 4)

    def testBuySellBuy(self):
        posTracker = returns.PositionTracker()
        posTracker.buy(1, 10)
        assert posTracker.getCost() == 10

        posTracker.sell(2, 13) # Short selling 1 @ $13
        assert posTracker.getCost() == 10 + 13

        posTracker.buy(1, 10)
        assert posTracker.getCost() == 10 + 13
        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price) == 6
        assert round(posTracker.getReturn(PosTrackerTestCase.invalid_price), 4) == round(0.260869565, 4)

    def testBuyAndUpdate(self):
        posTracker = returns.PositionTracker()
        posTracker.buy(1, 10)
        assert posTracker.getCost() == 10
        assert posTracker.getNetProfit(20) == 10
        assert posTracker.getReturn(20) == 1

        posTracker.update(15)
        assert posTracker.getCost() == 15
        assert posTracker.getNetProfit(15) == 0
        assert posTracker.getReturn(15) == 0

        assert posTracker.getNetProfit(20) == 5
        assert round(posTracker.getReturn(20), 2) == 0.33

    def testBuyUpdateAndSell(self):
        posTracker = returns.PositionTracker()
        posTracker.buy(1, 10)
        assert posTracker.getCost() == 10
        assert posTracker.getNetProfit(15) == 5
        assert posTracker.getReturn(15) == 0.5

        posTracker.update(15)
        assert posTracker.getCost() == 15
        posTracker.sell(1, 20)
        assert posTracker.getCost() == 15
        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price) == 5
        assert round(posTracker.getReturn(PosTrackerTestCase.invalid_price), 2) == 0.33

        posTracker.update(100)
        assert posTracker.getCost() == 0
        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price) == 0
        assert posTracker.getReturn(PosTrackerTestCase.invalid_price) == 0

    def testBuyAndSellBreakEvenWithCommision(self):
        posTracker = returns.PositionTracker()
        posTracker.buy(1, 10, 0.5)
        posTracker.sell(1, 11, 0.5)
        assert posTracker.getCost() == 10
        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price, False) == 1
        assert posTracker.getReturn(PosTrackerTestCase.invalid_price, False) == 0.1

        assert posTracker.getNetProfit(PosTrackerTestCase.invalid_price, True) == 0
        assert posTracker.getReturn(PosTrackerTestCase.invalid_price, True) == 0

    def testLongShortEqualAmount(self):
        posTrackerXYZ = returns.PositionTracker()
        posTrackerXYZ.buy(11, 10)
        posTrackerXYZ.sell(11, 30)
        assert posTrackerXYZ.getCost() == 11*10
        assert posTrackerXYZ.getNetProfit(PosTrackerTestCase.invalid_price) == 20*11
        assert posTrackerXYZ.getReturn(PosTrackerTestCase.invalid_price) == 2

        posTrackerABC = returns.PositionTracker()
        posTrackerABC.sell(100, 1.1)
        posTrackerABC.buy(100, 1)
        assert posTrackerABC.getCost() == 100*1.1
        assert round(posTrackerABC.getNetProfit(PosTrackerTestCase.invalid_price), 2) == 100*0.1
        self.assertEqual(round(posTrackerABC.getReturn(PosTrackerTestCase.invalid_price), 2), 0.09)

        combinedCost = posTrackerXYZ.getCost() + posTrackerABC.getCost()
        combinedPL = posTrackerXYZ.getNetProfit(PosTrackerTestCase.invalid_price) + posTrackerABC.getNetProfit(PosTrackerTestCase.invalid_price)
        combinedReturn = combinedPL / float(combinedCost)
        assert round(combinedReturn, 9) == 1.045454545

class ReturnsTestCase(unittest.TestCase):
    TestInstrument = "any"

    def testOneBarReturn(self):
        initialCash = 1000
        barFeed = yahoofeed.Feed()
        barFeed.setBarFilter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 07), strategy_test.datetime_from_date(2001, 12, 07)))
        barFeed.addBarsFromCSV(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.DummyStrategy(barFeed, initialCash)

        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the orders to get them filled on the first (and only) bar.
        order = strat.getBroker().createMarketOrder(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.74
        strat.getBroker().placeOrder(order)
        order = strat.getBroker().createMarketOrder(broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.91
        strat.getBroker().placeOrder(order)

        stratAnalyzer = returns.Returns()
        strat.attachAnalyzer(stratAnalyzer)
        strat.run()
        assert strat.getBroker().getCash() == initialCash + (15.91 - 15.74)

        finalValue = 1000 - 15.74 + 15.91
        rets = (finalValue - initialCash) / float(initialCash)
        self.assertEqual(stratAnalyzer.getReturns()[-1], rets)

    def testTwoBarReturns_OpenOpen(self):
        initialCash = 15.61
        barFeed = yahoofeed.Feed()
        barFeed.setBarFilter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 06), strategy_test.datetime_from_date(2001, 12, 07)))
        barFeed.addBarsFromCSV(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.DummyStrategy(barFeed, initialCash)

        # 2001-12-06,15.61,16.03,15.50,15.90,66944900,15.55
        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the entry order, to get it filled on the first bar.
        order = strat.getBroker().createMarketOrder(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.61
        strat.getBroker().placeOrder(order)
        strat.addOrder(strategy_test.datetime_from_date(2001, 12, 06), strat.getBroker().createMarketOrder, broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.74

        stratAnalyzer = returns.Returns()
        strat.attachAnalyzer(stratAnalyzer)
        strat.run()
        assert strat.getBroker().getCash() == initialCash + (15.74 - 15.61)
        # First day returns: Open vs Close
        assert stratAnalyzer.getReturns()[0] == (15.90 - 15.61) / 15.61
        # Second day returns: Open vs Prev. day's close
        assert stratAnalyzer.getReturns()[1] == (15.74 - 15.90) / 15.90

    def testTwoBarReturns_OpenClose(self):
        initialCash = 15.61
        barFeed = yahoofeed.Feed()
        barFeed.setBarFilter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 06), strategy_test.datetime_from_date(2001, 12, 07)))
        barFeed.addBarsFromCSV(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.DummyStrategy(barFeed, initialCash)

        # 2001-12-06,15.61,16.03,15.50,15.90,66944900,15.55
        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the entry order, to get it filled on the first bar.
        order = strat.getBroker().createMarketOrder(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.61
        strat.getBroker().placeOrder(order)
        strat.addOrder(strategy_test.datetime_from_date(2001, 12, 06), strat.getBroker().createMarketOrder, broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.91

        stratAnalyzer = returns.Returns()
        strat.attachAnalyzer(stratAnalyzer)
        strat.run()
        assert strat.getBroker().getCash() == initialCash + (15.91 - 15.61)
        # First day returns: Open vs Close
        assert stratAnalyzer.getReturns()[0] == (15.90 - 15.61) / 15.61
        # Second day returns: Close vs Prev. day's close
        assert stratAnalyzer.getReturns()[1] == (15.91 - 15.90) / 15.90

    def testTwoBarReturns_CloseOpen(self):
        initialCash = 15.9
        barFeed = yahoofeed.Feed()
        barFeed.setBarFilter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 06), strategy_test.datetime_from_date(2001, 12, 07)))
        barFeed.addBarsFromCSV(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.DummyStrategy(barFeed, initialCash)

        # 2001-12-06,15.61,16.03,15.50,15.90,66944900,15.55
        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the entry order, to get it filled on the first bar.
        order = strat.getBroker().createMarketOrder(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.90
        strat.getBroker().placeOrder(order)
        strat.addOrder(strategy_test.datetime_from_date(2001, 12, 06), strat.getBroker().createMarketOrder, broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.74

        stratAnalyzer = returns.Returns()
        strat.attachAnalyzer(stratAnalyzer)
        strat.run()
        assert strat.getBroker().getCash() == initialCash + (15.74 - 15.90)
        # First day returns: 0
        assert stratAnalyzer.getReturns()[0] == 0
        # Second day returns: Open vs Prev. day's close
        assert stratAnalyzer.getReturns()[1] == (15.74 - 15.90) / 15.90

    def testTwoBarReturns_CloseClose(self):
        initialCash = 15.90
        barFeed = yahoofeed.Feed()
        barFeed.setBarFilter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 06), strategy_test.datetime_from_date(2001, 12, 07)))
        barFeed.addBarsFromCSV(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.DummyStrategy(barFeed, initialCash)

        # 2001-12-06,15.61,16.03,15.50,15.90,66944900,15.55
        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the entry order, to get it filled on the first bar.
        order = strat.getBroker().createMarketOrder(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.90
        strat.getBroker().placeOrder(order)
        strat.addOrder(strategy_test.datetime_from_date(2001, 12, 06), strat.getBroker().createMarketOrder, broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.91

        stratAnalyzer = returns.Returns()
        strat.attachAnalyzer(stratAnalyzer)
        strat.run()
        assert strat.getBroker().getCash() == initialCash + (15.91 - 15.90)
        # First day returns: 0
        assert stratAnalyzer.getReturns()[0] == 0
        # Second day returns: Open vs Prev. day's close
        assert stratAnalyzer.getReturns()[1] == (15.91 - 15.90) / 15.90

    def testCumulativeReturn(self):
        initialCash = 33.06
        barFeed = yahoofeed.Feed()
        barFeed.addBarsFromCSV(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.DummyStrategy(barFeed, initialCash)

        strat.addPosEntry(strategy_test.datetime_from_date(2001, 1, 12), strat.enterLong, ReturnsTestCase.TestInstrument, 1) # 33.06
        strat.addPosExit(strategy_test.datetime_from_date(2001, 11, 27), strat.exitPosition) # 14.32

        stratAnalyzer = returns.Returns()
        strat.attachAnalyzer(stratAnalyzer)
        strat.run()
        assert round(strat.getBroker().getCash(), 2) == round(initialCash + (14.32 - 33.06), 2)
        assert round(33.06 * (1 + stratAnalyzer.getCumulativeReturns()[-1]), 2) == 14.32

    def testGoogle2011(self):
        initialValue = 1000000
        barFeed = yahoofeed.Feed()
        barFeed.addBarsFromCSV(ReturnsTestCase.TestInstrument, common.get_data_file_path("goog-2011-yahoofinance.csv"))

        strat = strategy_test.DummyStrategy(barFeed, initialValue)
        order = strat.getBroker().createMarketOrder(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1654, True) # 2011-01-03 close: 604.35
        strat.getBroker().placeOrder(order)

        stratAnalyzer = returns.Returns()
        strat.attachAnalyzer(stratAnalyzer)
        strat.run()
        finalValue = strat.getBroker().getValue(strat.getFeed().getLastBars())

        self.assertEqual(round(stratAnalyzer.getCumulativeReturns()[-1], 4), round((finalValue - initialValue) / float(initialValue), 4))
