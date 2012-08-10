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
from ib_testeclientsocket import TestEClientSocket

class IBConnectionTestCase(unittest.TestCase):
	def setUp(self):
		self.__testTWS = TestEClientSocket(self)
		self.__conn = Connection(eClientSocket=self.__testTWS)
		self.__conn.nextValidId(100) # Start with order id 100

	def testOrders(self): 
		instrument = 'XXX'
		trailingPct = 12 
		totalQty = 100
		minQty = 50
		goodTillDate = '20120420'
		whatif = False
		trailStopPrice = 13
		secType = 'STK'
		exchange = 'SMART'
		
		for currency in ('USD', 'EUR', 'GBP', 'HKD'):
			for action in ('BUY', 'SELL', 'SSHORT'):
				for orderType in ('MKT', 'LMT', 'STP', 'STP LMT'):
					for transmit in (True, False):
						for tif in ('DAY', 'GTC', 'IOC', 'GTD'):
							if orderType == 'MKT': 
								lmtPrice = 0 
								auxPrice = 0
							elif orderType == 'LMT':
								lmtPrice = 10
								auxPrice = 0
							elif orderType == 'STP':
								lmtPrice = 0 
								auxPrice = 11 
							elif orderType == 'STP LMT':
								lmtPrice = 11 
								auxPrice = 12 
							
							orderId = self.__conn.createOrder(instrument, action, lmtPrice, auxPrice, orderType, totalQty, minQty,
															  tif, goodTillDate, trailingPct, trailStopPrice, transmit, whatif,
															  secType, exchange, currency)
							self.assertEqual(instrument, self.__testTWS.orderContract.m_symbol)
							self.assertEqual(action, self.__testTWS.order.m_action)
							self.assertEqual(lmtPrice, self.__testTWS.order.m_lmtPrice)
							self.assertEqual(auxPrice, self.__testTWS.order.m_auxPrice)
							self.assertEqual(orderType, self.__testTWS.order.m_orderType)
							self.assertEqual(totalQty, self.__testTWS.order.m_totalQuantity)
							self.assertEqual(minQty, self.__testTWS.order.m_minQuantity)
							self.assertEqual(tif, self.__testTWS.order.m_tif)
							self.assertEqual(goodTillDate, self.__testTWS.order.m_goodTillDate)
							self.assertEqual(trailingPct, self.__testTWS.order.m_trailingPct)
							self.assertEqual(trailStopPrice, self.__testTWS.order.m_trailStopPrice)
							self.assertEqual(transmit, self.__testTWS.order.m_transmit)
							self.assertEqual(whatif, self.__testTWS.order.m_whatif)
							self.assertEqual(secType, self.__testTWS.orderContract.m_secType)
							self.assertEqual(exchange, self.__testTWS.orderContract.m_exchange)
							self.assertEqual(currency, self.__testTWS.orderContract.m_currency)

							self.assertEqual(orderId, self.__testTWS.orderId)
							self.assertGreaterEqual(self.__testTWS.orderId, 100)

							self.__conn.cancelOrder(orderId)
							
							self.assertTrue(self.__testTWS.order == None)
							self.assertTrue(self.__testTWS.orderId == None)
							self.assertTrue(self.__testTWS.orderContract == None)

	def testRealtimeBars(self): 
		global testHandlerCalls
		global testHandlerBar

		testHandlerCalls = 0
		testHandlerBar = None

		def testHandler(instrumentBar):
			instrument, bar = instrumentBar
			global testHandlerCalls
			global testHandlerBar
			testHandlerBar = bar
			testHandlerCalls += 1

		instrument = 'XXX'
		secType = 'STK'
		exchange = 'SMART'
		barSize = 5
		
		for currency in ('USD', 'EUR', 'GBP', 'HKD'):
			for whatToShow in ('TRADES', 'BID', 'ASK', 'MIDPOINT'):
				for useRTH in (0, 1): 
					self.__conn.subscribeRealtimeBars(instrument, testHandler, secType, exchange, currency, 
												  	  barSize, whatToShow, useRTH)

					self.assertEqual(instrument, self.__testTWS.realtimeContract.m_symbol)
					self.assertEqual(secType, self.__testTWS.realtimeContract.m_secType)
					self.assertEqual(exchange, self.__testTWS.realtimeContract.m_exchange)
					self.assertEqual(currency, self.__testTWS.realtimeContract.m_currency)
					self.assertEqual(barSize, self.__testTWS.realtimeBarSize)
					self.assertEqual(whatToShow, self.__testTWS.realtimeWhatToShow)
					self.assertEqual(useRTH, self.__testTWS.realtimeUseRTH)


					# Test for handler callback
					tickerId = self.__testTWS.realtimeTickerId
					time_ = time.mktime(datetime.datetime(2012, 04, 20, 15, 30, 05).utctimetuple())
					self.__conn.realtimeBar(tickerId, time_, 
											open_=1.1, high=1.5, low=1.0, close=1.3, volume=15, vwap=1.2, tradeCount=5)


					# Check if callback is reached the testHandler
					self.assertEqual(testHandlerCalls, 1)
					self.assertIsInstance(testHandlerBar, Bar)
					# self.assertEqual(testHandlerBar.getDateTime(), datetime.datetime(2012, 04, 20, 15, 30, 05))
					self.assertEqual(testHandlerBar.getOpen(), 1.1)
					self.assertEqual(testHandlerBar.getHigh(), 1.5)
					self.assertEqual(testHandlerBar.getLow(),  1.0)
					self.assertEqual(testHandlerBar.getClose(), 1.3)
					self.assertEqual(testHandlerBar.getVolume(), 15)
					self.assertEqual(testHandlerBar.getVWAP(), 1.2)
					self.assertEqual(testHandlerBar.getTradeCount(), 5)

					self.__conn.unsubscribeRealtimeBars(instrument, testHandler)
					
					# Should not dispatch after unsubscription
					self.__conn.realtimeBar(tickerId, time_, 
											open_=2.1, high=2.5, low=2.0, close=2.3, volume=12, vwap=2.2, tradeCount=2)
					self.assertEqual(testHandlerCalls, 1)
					self.assertIsInstance(testHandlerBar, Bar)
					# self.assertEqual(testHandlerBar.getDateTime(), datetime.datetime(2012, 04, 20, 15, 30, 05))
					self.assertEqual(testHandlerBar.getOpen(), 1.1)
					self.assertEqual(testHandlerBar.getHigh(), 1.5)
					self.assertEqual(testHandlerBar.getLow(),  1.0)
					self.assertEqual(testHandlerBar.getClose(), 1.3)
					self.assertEqual(testHandlerBar.getVolume(), 15)
					self.assertEqual(testHandlerBar.getVWAP(), 1.2)
					self.assertEqual(testHandlerBar.getTradeCount(), 5)

					testHandlerCalls = 0
					testHandlerBar = None
	
	def testHistoricalData(self): pass
	def testMarketScanner(self): pass
	def testAccountUpdates(self): pass
	def testGetCash(self): pass
	def testGetAccountValues(self): pass
	def testGetPortfolio(self): pass

def getTestCases():
	ret = []
	ret.append(IBConnectionTestCase("testOrders"))
	ret.append(IBConnectionTestCase("testRealtimeBars"))
	return ret

# vim: noet:ci:pi:sts=0:sw=4:ts=4
