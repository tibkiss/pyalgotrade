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
from pyalgotrade.stratanalyzer import sharpe
from pyalgotrade.broker import backtesting
from pyalgotrade import broker

import strategy_test
import common


class CalmarRatioTestCase(unittest.TestCase):
    def testNoTrades(self):
        barFeed = yahoofeed.Feed()
        barFeed.addBarsFromCSV("ige", common.get_data_file_path("sharpe-ratio-test-ige.csv"))
        strat = strategy_test.DummyStrategy(barFeed, 1000)
        stratAnalyzer = sharpe.SharpeRatio()
        strat.attachAnalyzer(stratAnalyzer)

        strat.run()
        assert strat.getBroker().getCash() == 1000
        assert stratAnalyzer.getSharpeRatio(0.04, 252, annualized=True) == 0
        assert stratAnalyzer.getSharpeRatio(0, 252) == 0
        assert stratAnalyzer.getSharpeRatio(0, 252, annualized=True) == 0
