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

import unittest
import pytest

from pyalgotrade import dataseries

# SciPy (therefore pyalgotrade.technical) is not available in pypy
try:
    from pyalgotrade.technical import trend
except ImportError:
    pytestmark = pytest.mark.skip(reason="SciPy is unavailable")

class TestCase(unittest.TestCase):
    def __buildTrend(self, values, trendDays, positiveThreshold, negativeThreshold):
        return trend.Trend(dataseries.SequenceDataSeries(values), trendDays, positiveThreshold, negativeThreshold)

    def testTrend(self):
        trend = self.__buildTrend([1, 2, 3, 2, 1], 3, 0, 0)
        assert trend[0] == None
        assert trend[1] == None
        assert trend[2] == True
        assert trend[3] == None
        assert trend[4] == False

        self.assertEqual(len(trend.getDateTimes()), 5)
        for i in range(len(trend)):
            self.assertEqual(trend.getDateTimes()[i], None)

    def testTrendWithCustomThresholds(self):
        trend = self.__buildTrend([1, 2, 3, 5, -10], 3, 1, -1)
        assert trend[0] == None
        assert trend[1] == None
        assert trend[2] == None
        assert trend[3] == True
        assert trend[4] == False

        self.assertEqual(len(trend.getDateTimes()), 5)
        for i in range(len(trend)):
            self.assertEqual(trend.getDateTimes()[i], None)

def getTestCases():
    ret = []
    ret.append(TestCase("testTrend"))
    ret.append(TestCase("testTrendWithCustomThresholds"))
    return ret
