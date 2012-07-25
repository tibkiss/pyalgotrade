# PyAlgoTrade
# 
# Related materials
# Interactive Brokers API:	http://www.interactivebrokers.com/en/software/api/api.htm
# IbPy: http://code.google.com/p/ibpy/ 
# 
# Copyright 2012 Gabriel Martin Becedillas Ruiz
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

import threading, copy, datetime
from time import localtime 

from pyalgotrade import observer

from ibbar import Bar

from ib.ext.EWrapper import EWrapper
from ib.ext.EClientSocket import EClientSocket
from ib.ext.ScannerSubscription import ScannerSubscription
from ib.ext.Contract import Contract
from ib.ext.Order import Order

import logging
log = logging.getLogger(__name__)

class Connection(EWrapper):
		'''Wrapper class for Interactive Brokers TWS Connection.

		This class exports the IB API's Order, Realtime- and Historical Market Data and Market Scanner features.

		The IB API architecture uses asynchronous callback based data model. The calls made synchronous where it makes
		sense (Order Execution, Historical Data & Market Scanner) and kept asynchronous with a subscription model for
		Realtime Data and Order Updates. 

		:param accountCode: Interactive Brokers Account Code. Shown in the right corner in TWS. Format: DUXXXXX
		:type accountCode: str
		:param timezone: the zone specifies the offset from coordinated universal time (utc, formerly referred to as 
						 "greenwich mean time")
		:type timezone: int
		:param twsHost: Hostname of the machine where the TWS is running. Default: localhost
		:type twsHost: str
		:param twsPort: Port number of the listening TWS. Default: 7496
		:type twsPort: int
		:param twsClientId: Client ID used for this TWS connection. Default: 27
		:type twsClientId: int
		'''

		def __init__(self, accountCode, timezone=0, twsHost='localhost', twsPort=7496, twsClientId=27):
				self.__accountCode = accountCode
				self.__zone = timezone
				self.__twsHost = twsHost
				self.__twsPort = twsPort
				self.__twsClientId = twsClientId

				# Errors returned by TWS, set by error()
				# Need to create this variable first as the client connection could
				# return error
				self.__error = {'tickerId': None, 'errorCode': None, 'errorString': None}

				# Unique Ticker ID stream for each TWS Request
				self.__tickerId = 0

				# Unique Order ID for each TWS Order
				# Initial value is set by nextValidId() callback
				self.__orderId = 0

				# Dictionary to map instruments to orderIds
				self.__orderIds = {}

				# Dictionary to map instruments to realtime bar tickerIds
				self.__realtimeBarIDs = {}

				# Dictionary to map instruments to realtime bar observer events
				self.__realtimeBarEvents = {}
				
				# Dictionary to map instruments to historical data tickerIds
				self.__historicalDataTickerIds = {}

				# List to buffer historical data which is produced by 
				# historicalData(), consumed by requestHistoricalData()
				self.__historicalDataBuffer = []

				# Lock for the historicalDataBuffer
				self.__historicalDataLock = threading.Condition()

				# Dictionary to map instruments to tickerIds for market scanner 
				self.__marketScannerIDs = {}
				
				# Lock for the historicalDataBuffer
				self.__marketScannerLock = threading.Condition()

				# List to buffer market scanner data between requestMarketScanner()
				# and scannerData 
				self.__marketScannerBuffer = []

				# Account and portfolio is represented by multidimensional maps
				# See updateAccountValue()/updatePortfolio() for valid keys
				self.__accountValues = {}
				self.__portfolio = {}

				# Conditional lock for account and portfolio updates
				self.__accUpdateLock = threading.Condition()
				self.__portfolioLock = threading.Condition()

				# Observer for Order Updates
				self.__orderUpdateHandler = observer.Event()

				# Create EClientSocket for TWS Connection
				self.__tws = EClientSocket(self)
				
				# Connection status
				self.__connected = False
				self.__accountUpdatesSubscribed = False


		def __getNextTickerId(self):
				"""Returns the next unique Ticker ID"""
				tickerId = copy.copy(self.__tickerId)
				self.__tickerId += 1
				return tickerId
		
		def __getNextOrderId(self):
				"""Returns the next unique Order ID"""
				orderId = copy.copy(self.__orderId)
				self.__orderId += 1
				return orderId

		def getTimezone(self):
				"""Returns the timezone. The zone specifies the offset from Coordinated Universal Time 
				(UTC, formerly referred to as "Greenwich Mean Time")
				"""
				return self.__zone
		
		def connect(self):
				"""Initiates TWS Connection"""
				if not self.__connected:
					log.info("Initiating TWS Connection (%s:%d, clientId=%d) with accountCode=%s" % 
						 	 (self.__twsHost, self.__twsPort, self.__twsClientId, self.__accountCode))

					self.__tws.eConnect(self.__twsHost, self.__twsPort, self.__twsClientId)
					self.__connected = True

		def disconnect(self):
				"""Disconnects from TWS"""
				if self.__connected:
					log.info("Disconnecting from TWS")
					self.__tws.eDisconnect()
					self.__connected = False

		########################################################################################
		# Requests for TWS
		########################################################################################
		def createOrder(self, instrument, action, lmtPrice, auxPrice, orderType, totalQty, minQty,
						tif, goodTillDate, trailingPct, trailStopPrice, transmit, whatif, 
						secType='STK', exchange='SMART', currency='USD' ):
				"""Creates a new order and sends it to the market via TWS
				
				:param instrument:
				:type instrument: str
				:param action: Identifies the side. Valid values are: BUY, SELL, SSHORT.
				:type action: str
				:param auxPrice: This is the STOP price for stop-limit orders, and the offset 
								 amount for relative orders. In all other cases, specify zero.
				:type auxPrice: float
				:param lmtPrice: This is the LIMIT price, used for limit, stop-limit and relative orders. 
								 In all other cases specify zero.
				:type lmtPrice: float
				:param orderType: Supported Order Types (this is just a subset of the IB's API, 
								  for the full list check the API):
								  STP, STP LMT, TRAIL LIT, TRAIL MIT, TRAIL, TRAIL LIMIT,
								  MKT, LMT, LOC, LOO, LIT		   
				:type orderType: str
				:param totalQty: The order quantity.
				:type totalQty: int
				:param minQty: Identifies a minimum quantity order type. 
				:type minQty: int
				:param tif: The time in force. Valid values are: DAY, GTC, IOC, GTD.
				:type tif: str
				:param goodTillDate: You must enter GTD as the time in force to use this string.
									 The trade's "Good Till Date," format "YYYYMMDD hh:mm:ss (optional time zone)
									 Use an empty String if not applicable.
				:type goodTillDate: str
				:param trailingPct: Specify the trailing amount of a trailing stop order as a percentage.
									Observe the following guidelines when using the trailingPercent field:
									 - This field is mutually exclusive with the existing trailing amount. 
									   That is, the API client can send one or the other but not both.
									 - This field is read AFTER the stop price (barrier price) as follows: 
									   deltaNeutralAuxPrice, stopPrice, trailingPercent, scale order attributes
									 - The field will also be sent to the API in the openOrder message if the API 
									   client version is >= 56. It is sent after the stopPrice field as follows:
									   stopPrice, trailingPct, basisPoint
				:type trailingPct: float
				:param trailStopPrice: For TRAILLIMIT orders only
				:type trailStopPrice: float
				:param transmit: Specifies whether the order will be transmitted by TWS. If set to false, the order
								 will be created at TWS but will not be sent.
				:type transmit: bool
				:param whatif: Use to request pre-trade commissions and margin information.
							   If set to true, margin and commissions data is received back via the OrderState()
							   object for the openOrder() callback.
				:type whatif: bool
				:param secType: This is the security type. Valid values are:
								STK, OPT, FUT, IND, FOP, CASH, BAG
				:type secType: str
				:param exchange: The order destination, such as Smart.
				:type exchange: str
				:param currency: Specifies the currency for the trade.
				:type currency: str
				"""
				self.connect()
				orderId = self.__getNextOrderId()

				self.__orderIds[orderId] = instrument
				
				contract = Contract()
				contract.m_symbol = instrument
				contract.m_secType = secType
				contract.m_exchange = exchange
				contract.m_currency = currency

				order = Order()
				order.m_action = action
				order.m_auxPrice = auxPrice
				order.m_lmtPrice = lmtPrice
				order.m_orderType = orderType
				order.m_totalQuantity = totalQty
				order.m_minQuantity = minQty
				order.m_goodTillDate = goodTillDate
				order.m_tif = tif
				order.m_trailingPct = trailingPct
				order.m_trailStopPrice = trailStopPrice
				order.m_transmit = transmit
				order.m_whatif = whatif

				self.__tws.placeOrder(orderId, contract, order)


		def cancelOrder(self, orderId):
				"""Cancels an order.
				
				:param orderId: Order ID.
				:type orderId: str
				"""
				self.connect()
				self.__tws.cancelOrder(orderId)

		def subscribeOrderUpdates(self, handler):
				"""Subscribes the handler for Order Updates from TWS.

				:param handler: Function which will be called on order state changes.
				:type handler: Function
				"""
				self.connect()
				self.__orderUpdateHandler.subscribe(handler)

		def subscribeRealtimeBars(self, instrument, handler, 
								  secType='STK', exchange='SMART', currency='USD', 
								  barSize=5, whatToShow='TRADES', useRTH=1):
				"""Subscribes handler for realtime market data of instrument.

				:param instrument: Instrument's symbol
				:type instrument: str
				:param handler: The function which will be called on new market data (every 5 secs)
				:type handler: Function
				:param secType: This is the security type. Valid values are:
								STK, OPT, FUT, IND, FOP, CASH, BAG
				:type secType: str
				:param exchange: The order destination, such as Smart.
				:type exchange: str
				:param currency: Specifies the currency for the trade.
				:type currency: str
				:param barSize: Specifies the size of the bars that will be returned (within IB/TWS limits). Valid values include:
								1 sec, 5 secs, 15 secs, 30 secs, 1 min, 2 mins, 3 mins, 5 mins, 15 mins, 30 mins, 1 hour, 1 day
				:type barSize:	str
				:param whatToShow: Determines the nature of data being extracted. Valid values include:
								   TRADES, MIDPOINT, BID, ASK, BID_ASK, HISTORICAL_VOLATILITY, OPTION_IMPLIED_VOLATILITY
				:type whatToShow: str
				:param useRTH: Determines whether to return all data available during the requested time span, 
							   or only data that falls within regular trading hours. Valid values include:
							   0: All data is returned even where the market in question was outside of its regular trading hours.
							   1: Only data within the regular trading hours is returned, even if the requested time span
							   falls partially or completely outside of the RTH.
				:type useRTH: int
				"""
				self.connect()
				if instrument not in self.__realtimeBarIDs:
						# Register the tickerId with the instrument name
						tickerId = self.__getNextTickerId()
						self.__realtimeBarIDs[instrument] = tickerId

						# Prepare the contract 
						contract = Contract()
						contract.m_symbol = instrument
						contract.m_secType = secType
						contract.m_exchange = exchange
						contract.m_currency = currency
						
						# Request realtime data from TWS
						self.__tws.reqRealTimeBars(tickerId, contract, barSize, whatToShow, useRTH)

						# Register handler for the realtime bar event observer
						self.__realtimeBarEvents[instrument] = observer.Event()
						self.__realtimeBarEvents[instrument].subscribe(handler)

				else:
						# Instrument already subscribed, add handler to the event observer
						self.__realtimeBarEvents[instrument].subscribe(handler)

		def unsubscribeRealtimeBars(self, instrument, handler):
				"""Cancels realtime data feed for the given instrument and handler.
				
				:param instrument: Instrument's symbol
				:type instrument: str
				:param handler: The function which will be called on new market data (every 5 secs)
				:type handler: Function
				"""
				self.connect()
				if instrument in self.__realtimeBarIDs:
						tickerId = self.__realtimeBarIDs[instrument]

						# TODO: Check for other observes and 
						# deregister only if last is freed
						self.__tws.cancelRealTimeBars(tickerId)

						del self.__realtimeBarIDs[instrument]
						del self.__realtimeBarEvents[instrument]
						del self.__realtimeBarBuffer[instrument]
				else:
						# Instrument was not subscribed, ignore
						pass

		def requestHistoricalData(self, instrument, endTime, duration, barSize,
								  secType='STK', exchange='SMART', currency='USD',
								  whatToShow='TRADES', useRTH=0, formatDate=1):
				"""Requests historical data. The historical bars are returned as a list of Bar instances.
				
				:param instrument: Instrument's symbol
				:type instrument: str
				:param endTime: Use the format yyyymmdd hh:mm:ss tmz, where the time zone is allowed (optionally) after a 
								space at the end.
				:type endTime:	str
				:param duration: This is the time span the request will cover, and is specified using the format: 
								 <integer> <unit>, i.e., 1 D, where valid units are:
								 S (seconds),  D (days),  W (weeks),  M (months),  Y (years)
								 If no unit is specified, seconds are used.  Also, note "years" is currently limited to one.
				:type duration: str
				:param barSize: Specifies the size of the bars that will be returned (within IB/TWS limits). Valid values include:
								1 sec, 5 secs, 15 secs, 30 secs, 1 min, 2 mins, 3 mins, 5 mins, 15 mins, 30 mins, 1 hour, 1 day
				:type barSize:	str
				:param secType: This is the security type. Valid values are:
								STK, OPT, FUT, IND, FOP, CASH, BAG
				:type secType: str
				:param exchange: The order destination, such as Smart.
				:type exchange: str
				:param currency: Specifies the currency for the trade.
				:type currency: str
				:param whatToShow: Determines the nature of data being extracted. Valid values include:
								   TRADES, MIDPOINT, BID, ASK, BID_ASK, HISTORICAL_VOLATILITY, OPTION_IMPLIED_VOLATILITY
				:type whatToShow: str
				:param useRTH: Determines whether to return all data available during the requested time span, 
							   or only data that falls within regular trading hours. Valid values include:
							   0: All data is returned even where the market in question was outside of its regular trading hours.
							   1: Only data within the regular trading hours is returned, even if the requested time span
							   falls partially or completely outside of the RTH.
				:type useRTH: int
				:param formatDate: Determines the date format applied to returned bars. Valid values include:
								   1: Dates applying to bars returned in the format: yyyymmdd{space}{space}hh:mm:dd .
								   2: Dates are returned as a long integer specifying the number of seconds since 1/1/1970 GMT .
				"""
				self.connect()

				# Get a unique tickerId for the request
				tickerId = self.__getNextTickerId()

				# Prepare the Contract for the historical data order
				contract = Contract()
				contract.m_symbol	= instrument;
				contract.m_secType	= secType;
				contract.m_exchange = exchange;
				contract.m_currency = currency;

				# map the tickerId to instrument
				self.__historicalDataTickerIds[tickerId] = instrument

				# Request historical data
				self.__tws.reqHistoricalData(tickerId, contract, endTime, duration, barSize, whatToShow, useRTH, formatDate)

				# Wait for the result to appear in the buffer
				self.__historicalDataLock.acquire()
				self.__historicalDataLock.wait()
				self.__historicalDataLock.release()

				# Copy the downloaded historical data and empty the buffer
				historicalData = copy.copy(self.__historicalDataBuffer)
				self.__historicalDataBuffer = []

				return historicalData 
				

		def requestMarketScanner(self, numberOfRows=10, 
								 scanCode='TOP_PERC_GAIN', stockTypeFilter='STOCK',
								 abovePrice=0.0, aboveVolume=0, 
								 locationCode='STK.US.MAJOR', instrument='STK'):
				"""
				This function receives the market scanner data and returns it as a list of 
				dicts with the following keys:
				instrument, secType, rank, distance, benchmark, projection, legsStr

				:param numberOfRows: Number of result rows to return
				:type numberOFRows: int
				:param scanCode: Market scanner code. Some of the available scanners:
								  - TOP_PERC_GAIN : Contracts whose last trade price shows the highest percent increase 
								  					from the previous night's closing price.
								  - TOP_PERC_LOSE : Contracts whose last trade price shows the lowest percent increase 
								  					from the previous night's closing price.
								  - MOST_ACTIVE   : Contracts with the highest trading volume today, based on units used 
								  					by TWS (lots for US stocks; contract for derivatives and non-US stocks).
								  - HOT_BY_VOLUME : Contracts where:
								  					 - today's Volume/avgDailyVolume is highest.
								  					 - avgDailyVolume is a 30-day exponential moving average of the contract's 
								  					   daily volume.
								  - HOT_BY_PRICE : Contracts where:
								  				 	 - (lastTradePrice-prevClose)/avgDailyChange is highest in absolute value 
								  				 	 	(positive  or negative).
								  					 - The avgDailyChange is defined as an exponential moving average of the 
								  					 	contract's (dailyClose-dailyOpen)
								  - TOP_PRICE_RANGE : The largest difference between today's high and low, or yesterday's close 
								  					   if outside of today's range.
								  - HOT_BY_PRICE_RANGE : The largest price range (from Top Price Range calculation) over the volatility.
								  - HIGH_OPEN_GAP   : Shows contracts with the highest percent price INCREASE between the previous close 
								  					  and today's opening prices.
								  - LOW_OPEN_GAP    : Shows contracts with the highest percent price DECREASE between the previous close and 
								  					  today's opening prices.
				:type scanCode: str
				:param stockTypeFilter: Stock type filter. Valid values: STOCK, ETF, ALL
				:type stockTypeFilter: str
				:param abovePrice: Filter out contracts with a price lower than this value. 
				:type abovePrice: float
				:param aboveVolume: Filter out contracts with a volume lower than this value.
				:type aboveVolume: int
				:param locationCode: The location code, valid values: 
									 - STK.US       : US stocks
									 - STK.US.MAJOR : US stocks (without pink sheet)
									 - STK.US.MINOR : US stocks (only pink sheet)
									 - STK.HK.SEHK  : Hong Kong stocks
									 - STK.HK.ASX   : Australian Stocks
									 - STK.EU       : European stocks
				:type locationCode: str
				:param instrument: Defines the instrument type for the scan.
				:type instrument: str
				"""
				self.connect()

				tickerId = self.__getNextTickerId()

				subscript = ScannerSubscription()
				subscript.numberOfRows(numberOfRows)
				subscript.locationCode(locationCode)
				subscript.abovePrice(float(abovePrice))
				subscript.aboveVolume(aboveVolume)
				subscript.scanCode(scanCode)
				subscript.instrument(instrument)
				subscript.stockTypeFilter(stockTypeFilter)

				self.__tws.reqScannerSubscription(tickerId, subscript)
				
				self.__marketScannerLock.acquire()
				self.__marketScannerLock.wait()
				self.__marketScannerLock.release()

				self.__tws.cancelScannerSubscription(tickerId)

				marketScannerData = copy.copy(self.__marketScannerBuffer)
				self.__marketScannerBuffer = []

				return marketScannerData

		def requestAccountUpdate(self):
				"""Subscribes for account updates"""
				self.connect()

				if not self.__accountUpdatesSubscribed:
					self.__tws.reqAccountUpdates(True, self.__accountCode)
					self.__accountUpdatesSubscribed = True

		def getCash(self, currency='USD'):
				"""Returns the cash (TotalCashBalance) available for the currency."""
				self.requestAccountUpdate()

				self.__accUpdateLock.acquire()
				
				# Try to load cash
				cash = None
				cashReturned = False
				while not cashReturned:
					try:
						cash = float(self.__accountValues[self.__accountCode][currency]['TotalCashBalance'])
					except KeyError:
						self.__accUpdateLock.wait()
					else:
						cashReturned = True

				self.__accUpdateLock.release()

				return(cash)

		def getAccountValues(self):
				self.requestAccountUpdate()
				return self.__accountValues

		def getPortfolio(self):
				self.requestAccountUpdate()
				return self.__portfolio

		########################################################################################
		# EWrapper callbacks
		########################################################################################
		def historicalData(self, tickerId, date, open_, high, low, close, volume, tradeCount, vwap, hasGaps):
				instrument = self.__historicalDataTickerIds[tickerId]

				# EOD is signaled in the date variable, eg.:
				# date='finished-20120628  00:00:00-20120630  00:00:00'
				if date.find("finished") != -1:
					# Signal the requestHistoricalData 
					self.__historicalDataLock.acquire()
					self.__historicalDataLock.notify()
					self.__historicalDataLock.release()
					
					return
						
				# Convert the time to local time
				dt = datetime.datetime.strptime(date, "%Y%m%d  %H:%M:%S")
				dt += datetime.timedelta(hours= (-1 * self.__zone))

				# Create the bar
				bar = Bar(instrument, dt, open_, high, low, close, volume, vwap, tradeCount)

				# Append it to the buffer
				self.__historicalDataBuffer.append(bar)

		def realtimeBar(self, tickerId, time_, open_, high, low, close, volume, vwap, tradeCount):
				"""
				This function receives the real-time bars data results and sends them to subscribers
				of __realtimeBarEvents.

				:param tickerId: The ticker Id of the request to which this bar is responding.
				:type tickerId: int
				:param time_: The date-time stamp of the start of the bar. The format is 
							  determined by the reqHistoricalData() formatDate parameter.
				:type time_: str
				:param open_: The bar opening price.
				:type open_: float
				:param high: The high price during the time covered by the bar.
				:type high: float
				:param low: The low price during the time covered by the bar.
				:type low: float
				:param close: The bar closing price.
				:type close: float
				:param volume: The volume during the time covered by the bar.
				:type volume: int
				:param vwap: The weighted average price during the time covered by the bar.
				:type vwap: float
				:param tradeCount: When TRADES historical data is returned, represents 
								   the number of trades that occurred during the time 
								   period the bar covers.
				:type tradeCount: int

				"""
				# Convert the timezone to the destination timezone
				lt = localtime(time_)
				dt = datetime.datetime(lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec)
				dt += datetime.timedelta(hours= (-1 * self.__zone))

				# Look up the instrument's name based on its tickerId
				for i in self.__realtimeBarIDs:
					if self.__realtimeBarIDs[i] == tickerId:
						instrument = i

				log.debug("RT Bar: %s [%d] time=%s open=%.2f high=%.2f low=%.2f close=%.2f volume=%d wap=%.2f tradeCount=%d" % 
						  (instrument, tickerId, dt, open_, high, low, close, volume, vwap, tradeCount))

				self.__realtimeBarEvents[instrument].emit(Bar(instrument, dt,
															  open_, high, low, close,
															  volume, vwap, tradeCount))

		
		def scannerData(self, reqId, rank, contractDetails, distance, benchmark, projection, legsStr=False):
				"""
				This function receives the requested market scanner data results and appends it to the
				market scanner buffer. A dict appended to the market scanner buffer with the following
				keys: instrument, secType, rank, distance, benchmark, projection, legsStr

				:param tickerId: The ticker ID of the request to which this row is responding.
				:type tickerId: int
				:param rank: The ranking within the response of this bar.
				:type rank: int
				:param contractDetails: This object contains a full description of the contract.
				:type contractDetails: :class:`ib.ext.ContractDetails` (IbPy)
				:param distance: Varies based on query.
				:type distance: str
				:param benchmark: Varies based on query.
				:type benchmark: str
				:param projection: Varies based on query.
				:type projection: str
				:param legsStr: Describes combo legs when scan is returning EFP.
				:type legsStr: str
				"""

				msd = { 'instrument': contractDetails.m_summary.m_symbol, 'secType': contractDetails.m_summary.m_secType,
						'rank': rank, 'distance': distance, 'benchmark': benchmark, 'projection': projection, 
						'legsStr': legsStr }
				self.__marketScannerBuffer.append(msd)

		def scannerDataEnd(self, reqId):
				"""This function is called when the snapshot is received and marks the end of one scan.
				This function will notify the requestMarketScanner() function that data is available in the buffer.

				:param tickerId: The ticker ID of the request to which this row is responding.
				:type tickerId: int
				"""
				self.__marketScannerLock.acquire()
				self.__marketScannerLock.notify()
				self.__marketScannerLock.release()

		def updateAccountValue(self, key, value, currency, accountName):
				"""
				This function is called only when ReqAccountUpdates has been called.
				It will notify the __accUpdateLock waiters (e.g. getCash()) if new data is available.

				:param key: A string that indicates one type of account value.
				:type key:	str
							Valid keys:
							CashBalance				- Account cash balance
							Currency				- Currency string
							DayTradesRemaining		- Number of day trades left
							EquityWithLoanValue		- Equity with Loan Value
							InitMarginReq			- Current initial margin requirement
							LongOptionValue			- Long option value
							MaintMarginReq			- Current maintenance margin
							NetLiquidation			- Net liquidation value
							OptionMarketValue		- Option market value
							ShortOptionValue		- Short option value
							StockMarketValue		- Stock market value
							UnalteredInitMarginReq	- Overnight initial margin requirement
							UnalteredMaintMarginReq - Overnight maintenance margin requirement
				:param value: The value associated with the key.
				:type value: str
				:param currency: Defines the currency type, in case the value is a currency type.
				:type currency: str
				:param account: States the account to which the message applies.
				:type account: str

				"""
				self.__accUpdateLock.acquire()

				# log.debug('updateAccountValue key=%s, value=%s, currency=%s, accountCode=%s' % (key, value, currency, accountName))
				self.__accountValues.setdefault(accountName, {})
				self.__accountValues[accountName].setdefault(currency, {})
				self.__accountValues[accountName][currency].setdefault(key, {})

				self.__accountValues[accountName][currency][key] = value

				self.__accUpdateLock.notify()
				self.__accUpdateLock.release()

		def updatePortfolio(self, contract, position, marketPrice, marketValue, 
							avgCost, unrealizedPNL, realizedPNL, accountName):
				"""
				This function is called only when ReqAccountUpdates has been called.
				It will notify the __portfolioLock waiters if new data is available.
				
				:param contract: This structure contains a description of the contract which 
								 is being traded. The exchange field in a contract is not set 
								 for portfolio update.
				:type contract: Contract
				:param position: This integer indicates the position on the contract. 
								 If the position is 0, it means the position has just cleared.
				:type position: int
				:param marketPrice: Unit price of the instrument.
				:type marketPrice: float
				:param marketValue: The total market value of the instrument.
				:type marketValue: float
				:param avgCost: The average cost per share is calculated by dividing your cost 
								(execution price + commission) by the quantity of your position.
				:type avgCost: float
				:param unrealizedPNL: The difference between the current market value of your 
									  open positions and the average cost, 
									  or Value - Average Cost.
				:type unrealizedPNL: float
				:param realizedPNL: Shows your profit on closed positions, which is the 
									difference between your entry execution cost 
									(execution price + commissions to open the position) and 
									exit execution cost (execution price + commissions to 
									close the position)
				:type realizedPNL: float
				:param accountName: States the account to which the message applies. 
				:type accountName: str

				"""
				log.debug("accountCode=%s, contract=%s, position=%d, marketPrice=%.2f, marketValue=%.2f, avgCost=%.2f, unrealizedPNL=%.2f, realizedPNL=%.2f" % 
						  (accountName, contract.m_symbol, position, marketPrice, marketValue, avgCost, unrealizedPNL, realizedPNL))
				instrument = contract.m_symbol

				self.__portfolioLock.acquire()

				self.__portfolio.setdefault(accountName, {})
				self.__portfolio[accountName].setdefault(instrument, {})

				self.__portfolio[accountName][instrument][contract] = contract
				self.__portfolio[accountName][instrument][position] = position
				self.__portfolio[accountName][instrument][marketPrice] = marketPrice
				self.__portfolio[accountName][instrument][marketValue] = marketValue
				self.__portfolio[accountName][instrument][avgCost] = avgCost
				self.__portfolio[accountName][instrument][unrealizedPNL] = unrealizedPNL
				self.__portfolio[accountName][instrument][realizedPNL] = realizedPNL
				
				self.__portfolioLock.notify()
				self.__portfolioLock.release()

		def updateAccountTime(self, timestamp): 
				"""This function is called only when reqAccountUpdates on EClientSocket object has been called.
				Logs the account update time.

				:param timestamp: This indicates the last update time of the account information
				:type timestamp: str
				"""
				log.debug("Last account update time: %s", timestamp)

		def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld):
				"""This event is called whenever the status of an order changes. It is also fired after 
				reconnecting to TWS if the client has any open orders.

				Note:  It is possible that orderStatus() may return duplicate messages. It is essential 
				that you filter the message accordingly.

				:param orderId: The order ID that was specified previously in the call to placeOrder()
				:type orderId: int
				:param status: The order status. Possible values include:
							   PendingSubmit, PendingCancel, PreSubmitted, Submitted, Cancelled, Filled, Inactive
				:type status: str
				:param filled: Specifies the number of shares that have been executed.
				:type filled: int
				:param remaining: Specifies the number of shares still outstanding.
				:type remaining: int 
				:param avgFillPrice: The average price of the shares that have been executed. This parameter 
									  is valid only if the filled parameter value is greater than zero. 
									  Otherwise, the price parameter will be zero.
				:type avgFillPrice: float
				:param permId: The TWS id used to identify orders. Remains the same over TWS sessions.
				:type permId: int
				:param parentId: The order ID of the parent order, used for bracket and auto trailing stop orders.
				:type parentId: int
				:param lastFillPrice: The last price of the shares that have been executed. 
									  This parameter is valid only if the filled parameter value is greater than zero. 
									  Otherwise, the price parameter will be zero.
				:type lastFillPrice: float
				:param clientId: The ID of the client (or TWS) that placed the order. Note that TWS orders have a fixed 
								 clientId and orderId of 0 that distinguishes them from API orders.
				:type clientId: int
				:param whyHeld: This field is used to identify an order held when TWS is trying to locate shares for a short sell. 
								The value used to indicate this is 'locate'.
				:type whyHeld: str
				"""
				log.debug("Order status: orderId: %s, status: %s, filled: %d, remaining: %d, avgFillPrice: %.2f, permId: %s, "
						 "parentId:%s, lastFillPrice: %.2f, clientId:%d, whyHeld: %s" % 
						 (orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId,	whyHeld))
				try:
					instrument = self.__orderIds[orderId]
				except KeyError:
					instrument = "UNKNOWN"

				self.__orderUpdateHandler.emit(orderId, instrument, status, filled, remaining, avgFillPrice, lastFillPrice)

		def openOrder(self, orderId, contract, order, orderState):
				log.debug("openOrder: orderId: %s, instrument: %s", orderId, contract.m_symbol)
				self.__orderIds[orderId] = contract.m_symbol

		def execDetails(self, orderId, contract, execution, liquidation):
				"""This event is fired when the reqExecutions() functions is invoked, or when an order is filled.
				
				:param orderId: The order ID that was specified previously in the call to placeOrder().
				:type orderId: int
				:param contract: This structure contains a full description of the contract that was executed.
				:type contract: :class:`IbPy.ext.Contract`
				:param execution: This structure contains addition order execution details.
				:type execution: :class:`IbPy.ext.Execution`
				:param liquidation: Not documented
				:type liquidation: Not documented

				"""
				pass

		def execDetailsEnd(self, reqId):
				"""This function is called once all executions have been sent to a client in response to reqExecutions().

				:param reqId: The Id of the data request.
				:type reqId: int
				"""
				pass

		def managedAccounts(self, accountsList): 
				"""Logs the managed account list by this TWS connection."""
				log.debug("Managed account list: %s", accountsList)
		
		def nextValidId(self, orderId): 
				"""This function is called after a successful connection to TWS.

				The next available order ID received from TWS upon connection. 
				Increment all successive orders by one based on this ID.
				"""
				self.__orderId = orderId

				log.debug("First valid orderId: %d", orderId)

		def error(self, tickerId, errorCode=None, errorString=None):
				"""Error handler function for the IB Connection."""
				self.__error['tickerId'] = tickerId
				self.__error['errorCode'] = errorCode
				self.__error['errorString'] = errorString

				if 0 <= errorCode < 1000:
						# Errors
						log.error( '%s, %s, %s' %(tickerId, errorCode, errorString))
				elif 1000 <= errorCode < 2000:
						# System messages
						log.info( 'System message: %s, %s, %s' %(tickerId, errorCode, errorString))
				elif 2000 <= errorCode < 3000:
						# Warning messages
						log.warn( '%s, %s, %s' %(tickerId, errorCode, errorString))

				if tickerId != -1:
						log.error( 'error: %s, %s, %s' %(tickerId, errorCode, errorString))

		def getError(self):
				"""Returns the error dictionary.
				Keys: tickerId, errorCode, errorString
				"""
				return self.__error

		def winError(self, errorMsg, errorCode): 
				"""Error handler function for the TWS Client side errors."""
				log.error("WINERROR: %d: %s", errorCode, errorMsg)

		def connectionClosed(self):
				"""Connection closed handler for the IB Connection."""
				log.error("Connection closed")

# vim: noet:ci:pi:sts=0:sw=4:ts=4
