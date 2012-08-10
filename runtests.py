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
from testcases import technical_test
from testcases import technical_ma_test
from testcases import technical_ratio_test
from testcases import technical_trend_test
from testcases import technical_rsi_test
from testcases import technical_cross_test
from testcases import technical_roc_test
from testcases import technical_stoch_test
from testcases import dataseries_test
from testcases import csvbarfeed_test
from testcases import broker_test
from testcases import strategy_test
from testcases import smacrossover_strategy_test
from testcases import talib_test
from testcases import observer_test
from testcases import ibconnection_test
from testcases import ibfeed_test
from testcases import ibbroker_test

def getTestCases():
	ret = []
	ret += technical_test.getTestCases()
	ret += technical_ma_test.getTestCases()
	ret += technical_ratio_test.getTestCases()
	ret += technical_trend_test.getTestCases()
	ret += technical_rsi_test.getTestCases()
	ret += technical_cross_test.getTestCases()
	ret += technical_roc_test.getTestCases()
	ret += technical_stoch_test.getTestCases()
	ret += dataseries_test.getTestCases()
	ret += csvbarfeed_test.getTestCases()
	ret += broker_test.getTestCases()
	ret += strategy_test.getTestCases()
	ret += smacrossover_strategy_test.getTestCases()
	ret += talib_test.getTestCases()
	ret += observer_test.getTestCases()
        ret += ibconnection_test.getTestCases()
        ret += ibfeed_test.getTestCases()
        ret += ibbroker_test.getTestCases()
	return ret

def main():
	suite = unittest.TestSuite()
	suite.addTests(getTestCases())
	runner = unittest.TextTestRunner(verbosity=2)
	runner.run(suite)

if __name__ == "__main__":
	main()

