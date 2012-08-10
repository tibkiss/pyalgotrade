# PyAlgoTrade
# 
# Copyright 2011 Gabriel Martin Becedillas Ruiz
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#	http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Tibor Kiss <tibor.kiss@gmail.com>
"""

import unittest
import time, datetime


from pyalgotrade.providers.interactivebrokers.ibconnection import Connection
from pyalgotrade.providers.interactivebrokers.ibbar import Bar
from pyalgotrade.providers.interactivebrokers.ibfeed import LiveFeed
from pyalgotrade.providers.interactivebrokers.ibbroker import FlatRateCommission, Order, MarketOrder, LimitOrder, StopOrder, StopLimitOrder, Broker
from ib_testeclientsocket import TestEClientSocket


class IBBrokerTestCase(unittest.TestCase):
	def setUp(self):
		self.__testTWS = TestEClientSocket(self)
		self.__conn = Connection(eClientSocket=self.__testTWS)
		self.__feed = LiveFeed(self.__conn)
		# self.__broker = Broker(self.__feed, self.__conn)


	def testFlatRateCommission(self):
	    # US API Directed Orders (example from IB Website):
	    # 100 Shares @ USD 25 Share Price = USD 1.30
	    # 700 Shares @ USD 25 Share Price = USD 8.10
	    comm = FlatRateCommission()
	    self.assertEqual(comm.calculate(order=None, price=25, quantity=100), 1.30)
	    self.assertEqual(comm.calculate(order=None, price=25, quantity=700), 8.10)


	def testOrders(self): pass


def getTestCases():
	ret = []
	ret.append(IBBrokerTestCase("testFlatRateCommission"))
	ret.append(IBBrokerTestCase("testOrders"))
	return ret

# vim: noet:ci:pi:sts=0:sw=4:ts=4
