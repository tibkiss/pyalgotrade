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
.. moduleauthor:: Tibor Kiss <tibor.kiss@gmail.com>
"""

import pytest
import unittest

from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.stratanalyzer import sortino
from pyalgotrade.broker import backtesting
from pyalgotrade import broker

import strategy_test
import common

class SharpeRatioTestCase(unittest.TestCase):
    def testNoTrades(self):
        barFeed = yahoofeed.Feed()
        barFeed.addBarsFromCSV("ige", common.get_data_file_path("sharpe-ratio-test-ige.csv"))
        strat = strategy_test.DummyStrategy(barFeed, 1000)
        stratAnalyzer = sortino.SortinoRatio()
        strat.attachAnalyzer(stratAnalyzer)

        strat.run()
        assert strat.getBroker().getCash() == 1000
        assert stratAnalyzer.getSortinoRatio() == 0

    def testIGE_BrokerWithCommission(self):
        commision = 0.5
        initialCash = 42.09 + commision
        # This testcase is based on an example from Ernie Chan's book:
        # 'Quantitative Trading: How to Build Your Own Algorithmic Trading Business'
        barFeed = yahoofeed.Feed()
        barFeed.addBarsFromCSV("ige", common.get_data_file_path("sharpe-ratio-test-ige.csv"))
        brk = backtesting.Broker(initialCash, barFeed, backtesting.FixedCommission(commision))
        strat = strategy_test.DummyStrategy(barFeed, initialCash, brk)
        strat.getBroker().setUseAdjustedValues(True)
        strat.setBrokerOrdersGTC(True)
        stratAnalyzer = sortino.SortinoRatio()
        strat.attachAnalyzer(stratAnalyzer)

        # Manually place the order to get it filled on the first bar.
        order = strat.getBroker().createMarketOrder(broker.Order.Action.BUY, "ige", 1, True) # Adj. Close: 42.09
        order.setGoodTillCanceled(True)
        strat.getBroker().placeOrder(order)
        strat.addOrder(strategy_test.datetime_from_date(2007, 11, 13), strat.getBroker().createMarketOrder, broker.Order.Action.SELL, "ige", 1, True) # Adj. Close: 127.64
        strat.run()
        assert round(strat.getBroker().getCash(), 2) == initialCash + (127.64 - 42.09 - commision*2)
        assert strat.getOrderUpdatedEvents() == 2
        assert round(stratAnalyzer.getSortinoRatio(), 4) == 1.375

    def testSortinoCalculation_Redrock(self):
        # Based on http://www.redrockcapital.com/Sortino__A__Sharper__Ratio_Red_Rock_Capital.pdf
        annual_returns = [0.17, 0.15, 0.23, -0.05, 0.12, 0.09, 0.13, -0.04]
        target_return = 0

        result = sortino.sortino_ratio(annual_returns, target_return, annualized=False)

        assert round(result, 3) == 4.417

    def testSortinoCalculation_Random(self):
        daily_returns = [0.0268, -0.0399, -0.019, -0.0277, -0.0282, -0.0264, -0.0183, 0.0314, -0.0141, -0.0244]
        target_return = 0

        result = sortino.sortino_ratio(daily_returns, target_return)

        assert round(result, 3) == -9.602

    def testSortinoCalculation_Sunrise(self):
        # Based on http://www.sunrisecapital.com/wp-content/uploads/2014/06/Futures_Mag_Sortino_0213.pdf

        annual_returns = [0.02, 0.01, -0.01, 0.18, 0.08, -0.02, 0.01, -0.01]
        target_return = 0

        result = sortino.sortino_ratio(annual_returns, target_return, annualized=False)

        assert round(result, 2) == 3.75

    @pytest.mark.xfail(strict=True)
    def testSortinoCalculation_IBPerf(self):
        # Based on Huba's performance for time period 2016. 08. 19. - 08. 29.
        daily_returns = [0.0025, 0.0017, 0.0041, 0.0002, 0.0007, 0.0005, -0.0029,
                         -0.0063, -0.0059, 0.0007, 0.0027, 0, -0.0020, -0.0034, 0.0015, -0.0010]

        target_return = 0

        result = sortino.sortino_ratio(daily_returns, target_return)

        assert round(result, 2) == -4.73