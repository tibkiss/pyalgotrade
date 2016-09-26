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

from pyalgotrade import stratanalyzer
from pyalgotrade.stratanalyzer import returns
from pyalgotrade.utils import stats
import numpy as np
import math

def sortino_ratio(returns, target_return=0, annualized=True):
    """Sortino is an adjusted ratio which only takes the standard deviation of negative returns into account
    Calculation is based on the formula described at:
    http://www.redrockcapital.com/Sortino__A__Sharper__Ratio_Red_Rock_Capital.pdf
    """

    avg_period_return = np.mean(returns)
    target_returns = np.array(returns) - target_return

    negative_return_sum = np.sum([e**2 for e in target_returns if e < 0])
    target_downside_avg = negative_return_sum / len(target_returns)
    target_downside_deviation = np.sqrt(target_downside_avg)


    if target_downside_deviation > 0.0001:
        # Assuming daily returns: https://sixfigureinvesting.com/2013/09/daily-scaling-sharpe-sortino-excel/
        sortino = ((avg_period_return - target_return) / target_downside_deviation)

        if annualized:
            sortino *= math.sqrt(252)
    else:
        sortino = 0

    return sortino

def days_traded(begin, end):
    delta = end - begin
    ret = delta.days + 1
    return ret

class SortinoRatio(stratanalyzer.StrategyAnalyzer):
    """A :class:`pyalgotrade.stratanalyzer.StrategyAnalyzer` that calculates
    Sharpe ratio for the whole portfolio."""

    def __init__(self):
        self.__netReturns = []

    def beforeAttach(self, strat):
        # Get or create a shared ReturnsAnalyzerBase
        analyzer = returns.ReturnsAnalyzerBase.getOrCreateShared(strat)
        analyzer.getEvent().subscribe(self.__onReturns)

    def __onReturns(self, returnsAnalyzerBase):
        self.__netReturns.append(returnsAnalyzerBase.getNetReturn())

    def getSortinoRatio(self, targetReturns=0):
        return sortino_ratio(self.__netReturns, targetReturns, annualized=True)
