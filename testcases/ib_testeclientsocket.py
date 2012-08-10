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
.. moduleauthor:: Tibor Kiss <tibor.kiss@gmail.com>
"""

import time

from ib.ext.EClientSocket import EClientSocket
from ib.ext.ScannerSubscription import ScannerSubscription
from ib.ext.Contract import Contract
from ib.ext.Order import Order

class TestEClientSocket(EClientSocket):
	def __init__(self, testcase):
		# Testcase
		self.tc  = testcase

		# Connect / Disconnect
		self.host      = None
		self.port      = None
		self.clientId  = None
		self.connected = None

		# List of used order and tickerIds to check uniqueness
		self.orderIds  = [] 
		self.tickerIds = [] 

		# Scanner
		self.scannerTickerId	 = None
		self.scannerSubscription = None

		# Historical data
		self.historicalTickerId = None
		self.historicalContract = None
		self.historicalEndTime	= None 
		self.historicalDuration = None 
		self.historicalBarSize	= None 
		self.historicalWhatShow = None 
		self.historicalUseRTH	= None 
		self.historicalFormat	= None 

		# Realtime data
		self.realtimeTickerIds	= {}
		self.realtimeContract	= None
		self.realtimeBarSize	= None
		self.realtimeWhatToShow = None 
		self.realtimeUseRTH	= None 

		# Order
		self.order	   = None
		self.orderId	   = None
		self.orderContract = None


	def eConnect(self, host, port, clientId):
		self.tc.assertFalse(self.connected == True)

		self.tc.assertIsInstance(host, str)
		self.tc.assertIsInstance(port, int)
		self.tc.assertIsInstance(clientId, int)

		self.host = host
		self.port = port
		self.clientId = clientId
		self.conncted = True

	def eDisconnect(self):
		self.tc.assertTrue(self.connected == True)

		self.host      = None
		self.port      = None
		self.clientId  = None
		self.connected = False

	def reqScannerSubscription(self, tickerId, subscription):
		self.tc.assertTrue(self.connected == True)
		self.tc.assertTrue(self.tickerId == None)
		self.tc.assertIsInstance(tickerId, int)
		self.tc.assertIsInstance(subscription, ScannerSubscription)

		self.tc.assertNotIn(tickerId, self.tickerIds)
		self.tickerIds.append(tickerId)

		self.__checkScannerSubscription(subscription)

		self.scannerTickerId	 = tickerId
		self.scannerSubscription = subscription

	def cancelScannerSubscription(self, tickerId):
		self.tc.assertIsInstance(tickerId, int)
		self.tc.assertTrue(self.scannerTickerId == tickerId)

		self.scannerTickerId	 = None
		self.scannerSubscription = None

	def reqRealTimeBars(self, tickerId, contract, barSize, whatToShow, useRTH):
		self.tc.assertIsInstance(tickerId, int)
		self.tc.assertIsInstance(barSize, int)
		self.tc.assertIsInstance(whatToShow, str)
		self.tc.assertIsInstance(useRTH, int)

		self.tc.assertEquals(barSize, 5)
		self.tc.assertIn(whatToShow, ('TRADES', 'BID', 'ASK', 'MIDPOINT'))
		
		# Record the used tickerIds and check uniqueness
		self.tc.assertNotIn(tickerId, self.tickerIds)
		self.tickerIds.append(tickerId)

		self.realtimeTickerIds[tickerId] = True

		self.__checkContract(contract)

		self.realtimeTickerId	= tickerId
		self.realtimeContract	= contract
		self.realtimeBarSize	= barSize
		self.realtimeWhatToShow = whatToShow 
		self.realtimeUseRTH	= useRTH 

	def cancelRealTimeBars(self, tickerId):
		self.tc.assertIsInstance(tickerId, int)
		self.tc.assertIn(tickerId, self.realtimeTickerIds)
		del self.realtimeTickerIds[tickerId]

		self.realtimeContract	= None
		self.realtimeBarSize	= None
		self.realtimeWhatToShow = None 
		self.realtimeUseRTH  	= None 

	def reqHistoricalData(self, tickerId, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate):
		self.tc.assertTrue(self.historicalTickerId == None)
		self.tc.assertIsInstance(tickerId, int)
		self.tc.assertIsInstance(endDateTime, str)
		self.tc.assertIsInstance(durationStr, str)
		self.tc.assertIsInstance(barSizeSetting, str)
		self.tc.assertIsInstance(whatToShow, str)
		self.tc.assertIsInstance(useRTH, bool)
		self.tc.assertIsInstance(formatDate, int)

		dur = durationStr.split(" ")
		self.tc.assertTrue(len(dur) == 2)
		self.tc.assertGreater(int(dur[0]), 0)
		self.tc.assertIn(dur[1], ('S', 'D', 'W', 'M', 'Y'))
		
		self.tc.assertIn(barSizeSetting, ('1 sec', '5 secs', '15 secs', '30 secs', 
										  '1 min', '2 mins', '3 mins', '5 mins', '30 mins', 
										  '1 hour', '1 day'))
		self.tc.assertIn(whatToShow, ('TRADES', 'BID', 'ASK', 'MIDPOINT'))

		self.tc.assertIn(formatDate, (1, 2))

		self.tc.assertNotIn(tickerId, self.tickerIds)
		self.tickerIds.append(tickerId)

		self.__checkContract(contract)

		self.historicalTickerId = tickerId
		self.historicalContract = contract
		self.historicalEndTime	= endDateTime 
		self.historicalDuration = durationStr 
		self.historicalBarSize	= barSizeSetting 
		self.historicalWhatShow = whatToShow 
		self.historicalUseRTH	= useRTH 
		self.historicalFormat	= formatDate 

	def cancelHistoricalData(self, tickerId):
		self.tc.assertIsInstance(tickerId, int)
		self.tc.assertEquals(tickerId, self.historicalTickerId)

		self.historicalTickerId = None
		self.historicalContract = None
		self.historicalEndTime	= None 
		self.historicalDuration = None 
		self.historicalBarSize	= None 
		self.historicalWhatShow = None 
		self.historicalUseRTH	= None 
		self.historicalFormat	= None 

	def reqContractDetails(self, contract):
		self.__checkContract(contract)

	def reqAccountUpdates(self, subscribe, acctCode):
		self.tc.assertIsInstance(subscribe, bool)
		self.tc.assertIsInstance(acctCode, str)

	def placeOrder(self, id, contract, order):
		self.tc.assertEqual(self.orderId, None)

		self.tc.assertIsInstance(id, int)
		self.tc.assertNotIn(id, self.orderIds)
		self.orderIds.append(id)

		self.__checkContract(contract)
		self.__checkOrder(order)

		self.order = order
		self.orderId = id
		self.orderContract = contract

	def cancelOrder(self, id):
		self.tc.assertIsInstance(id, int)
		self.tc.assertEqual(id, self.orderId)

		self.order	   = None
		self.orderId	   = None
		self.orderContract = None

	def reqOpenOrders(self):
		pass

	def reqManagedAccts(self):
		pass

	def __checkOrder(self, order):
		self.tc.assertIsInstance(order, Order)
		self.tc.assertIn(order.m_action, ('BUY', 'SELL', 'SSHORT'))
		self.tc.assertIn(order.m_orderType, ('MKT', 'LMT', 'STP', 'STP LMT'))

		if order.m_orderType == 'MKT':
			self.tc.assertEqual(order.m_lmtPrice, 0)
			self.tc.assertEqual(order.m_auxPrice, 0)

		# lmtPrice: This is the LIMIT price, used for limit, stop-limit and relative orders. In all other cases specify zero. 
		# For relative orders with no limit price, also specify zero.
		if order.m_orderType in ('LMT', 'STP LMT'):
			self.tc.assertGreater(order.m_lmtPrice, 0)
		else:
			self.tc.assertEqual(order.m_lmtPrice, 0)

		# auxPrice: This is the STOP price for stop-limit orders, and the offset amount for relative orders. 
		# In all other cases, specify zero.
		if order.m_orderType in ('STP', 'STP LMT'):
			self.tc.assertGreater(order.m_auxPrice, 0)
		else:
			self.tc.assertEqual(order.m_auxPrice, 0)

		self.tc.assertIsInstance(order.m_allOrNone, bool)
		self.tc.assertIsInstance(order.m_minQuantity, int)
		self.tc.assertGreater(order.m_minQuantity, 0)
		self.tc.assertIsInstance(order.m_totalQuantity, int)
		self.tc.assertGreater(order.m_totalQuantity, 0)
		self.tc.assertIsInstance(order.m_outsideRth, bool)
		self.tc.assertIn(order.m_tif, ('DAY', 'GTC', 'IOC', 'GTD'))
		self.tc.assertIsInstance(order.m_transmit, bool)


	def __checkContract(self, contract):
		self.tc.assertIsInstance(contract, Contract)
		self.tc.assertIn(contract.m_currency, ('', 'USD', 'EUR', 'GBP', 'HKD'))
		self.tc.assertIn(contract.m_exchange, ('SMART', 'SMART_ECN', 'SEKH', ))
		if contract.m_expiry != '':
			self.tc.assertIsInstance(time.strptime(contract.m_expiry, '%Y%m%d'), time.struct_time)
		self.tc.assertIn(contract.m_secType, ('STK', 'OPT', 'FUT', 'IND', 'FOP', 'CASH', 'BAG'))
		self.tc.assertIsInstance(contract.m_symbol, str)
		self.tc.assertIsNot(contract.m_symbol, '')

	def __checkScannerSubscription(self, subscription):
		self.tc.assertIsInstance(subscription.m_abovePrice, int)
		self.tc.assertGreaterEqual(subscription.m_abovePrice, 0)
		self.tc.assertIsInstance(subscription.m_aboveVolume, int)
		self.tc.assertGreaterEqual(subscription.m_aboveVolume, 0)
		self.tc.assertIn(subscription.m_locationCode, ('STK.US', 'STK.US.MAJOR', 'STK.US.MINOR',
							       'STK.HK.SEHK', 'STK.HK.ASX', 'STK.EU'))
		self.tc.assertIn(subscription.m_scanCode, ('TOP_PERC_GAIN', 'TOP_PERC_LOSE', 'MOST_ACTIVE', 
							   'HOT_BY_VOLUME', 'HOT_BY_PRICE', 'TOP_TRADE_COUNT',
							   'TOP_TRADE_RATE', 'TOP_PRICE_RANGE', 'HOT_BY_PRICE_RANGE',
							   'TOP_VOLUME_RATE', 'TOP_OPEN_PERC_GAIN', 'TOP_OPEN_PERC_LOSE',
							   'HIGH_OPEN_GAP', 'LOW_OPEN_GAP'))
		self.tc.assertIn(subscription.m_stockTypeFilter, ('ALL', 'STOCK', 'ETF'))


# vim: noet:ci:pi:sts=0:sw=4:ts=4
