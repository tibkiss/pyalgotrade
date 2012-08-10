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
#

"""
.. moduleauthor:: Tibor Kiss <tibor.kiss@gmail.com>
"""


from pyalgotrade import broker

import logging
log = logging.getLogger(__name__)

######################################################################
## Commissions

class FlatRateCommission(broker.Commission):
	"""Flat Rate - US API Directed Orders
	Value			 Flat Rate		Minimum Per Order	Maximum Per Order
	< = 500 shares	$0.013/share		USD 1.30		0.5% of trade value
	> 500 shares	$0.008/share		USD 1.30		0.5% of trade value
	"""
	def calculate(self, order, price, quantity):
		minPerOrder=1.3
		maxPerOrder=(price * quantity) * 0.005 
		if quantity <= 500:
			flatRate = 0.013 * quantity
		else:
			flatRate = 0.013 * 500 + 0.008 * (quantity - 500)

		commission = max(minPerOrder, flatRate)
		commission = min(maxPerOrder, commission)

		log.debug("Flat rate commission: price=%.2f, quantity=%d minPerOrder=%.2f, maxPerOrder=%.4f, flatRate=%.4f. => commission=%.2f" %
				  (price, quantity, minPerOrder, maxPerOrder, flatRate, commission))

		return commission

######################################################################
## Orders

class Order(broker.Order):
	def __init__(self, ibConnection, type_, action, instrument, price, quantity, goodTillCanceled=False):
		broker.Order.__init__(self, type_, action, instrument, price, quantity, goodTillCanceled)
		self.__ibConnection = ibConnection
		self.__orderId = None

	def setOrderId(self, orderId):
		self.__orderId = orderId

	def getOrderId(self):
		return self.__orderId

	def setCanceled(self):
		# Just set the flag to canceled
		broker.Order.cancel(self)

	def cancel(self):
		# Ask the broker to cancel the position
		if self.__orderId != None:
			self.__ibConnection.cancelOrder(self.__orderId)
		
		# The canceled flag will be updated through the Broker's __orderUpdate()

class MarketOrder(Order):
	def __init__(self, ibConnection, action, instrument, quantity, goodTillCanceled=False):
		price = 0
		Order.__init__(self, ibConnection, Order.Type.MARKET, action, instrument, price, quantity, goodTillCanceled)

class LimitOrder(Order):
	def __init__(self, ibConnection, action, instrument, price, quantity, goodTillCanceled=False):
		Order.__init__(self, ibConnection, Order.Type.LIMIT, action, instrument, price, quantity, goodTillCanceled)
	
class StopOrder(Order):
	def __init__(self, ibConnection, action, instrument, price, quantity, goodTillCanceled=False):
		Order.__init__(self, ibConnection, Order.Type.STOP, action, instrument, price, quantity, goodTillCanceled)

class StopLimitOrder(Order):
	def __init__(self, ibConnection, action, instrument, limitPrice, stopPrice, quantity, goodTillCanceled=False):
		Order.__init__(self, ibConnection, Order.Type.STOP_LIMIT, action, instrument, limitPrice, quantity, goodTillCanceled)

		self.__stopPrice = stopPrice
		self.__limitOrderActive = False # Set to true when the limit order is activated (stop price is hit)
		
	def getStopPrice(self):
		return self.__stopPrice

	def setLimitOrderActive(self, limitOrderActive):
		self.__limitOrderActive = limitOrderActive

	def isLimitOrderActive(self):
		return self.__limitOrderActive

######################################################################
## Broker

class Broker(broker.BasicBroker):
	"""Class responsible for forwarding orders to Interactive Brokers Gateway via TWS.

	:param ibConnection: Object responsible to forward requests to TWS.
	:type ibConnection: :class:`IBConnection`
	"""
	def __init__(self, barFeed, ibConnection):
		self.__ibConnection = ibConnection
		self.__barFeed		= barFeed

		# Query the server for available funds
		self.__cash = self.__ibConnection.getCash()

		# Subscribe for order updates from TWS
		self.__ibConnection.subscribeOrderUpdates(self.__orderUpdate)

		# Local buffer for Orders. Keys are the orderIds
		self.__orders = {}

		# Call the base's constructor
		broker.BasicBroker.__init__(self, self.__cash)

	def __orderUpdate(self, orderId, instrument, status, filled, remaining, avgFillPrice, lastFillPrice):
		"""Handles order updates from IBConnection. Processes its status and notifies the strategy's __onOrderUpdate()"""

		log.debug('orderUpdate: orderId=%d, instrument=%s, status=%s, filled=%d, remaining=%d, avgFillPrice=%.2f, lastFillPrice=%.2f' % 
				  (orderId, instrument, status, filled, remaining, avgFillPrice, lastFillPrice))

		# Try to look up order (:class:`broker.Order`) from the local buffer
		# It is possible that the orderId is not present in the buffer: the
		# order could been created from another client (e.g. TWS). 
		# In such cases the order update will be ignored.
		try:
			order = self.__orders[orderId]
		except KeyError:
			log.warn("Order is not registered with orderId: %d, ignoring update" % orderId)
			return

		# Check for order status and set our local order accordingly
		if status == 'Cancelled':
			order.setCanceled()
		elif status == 'PreSubmitted':
			# Skip, we do not have the corresponding state in :class:`broker.Order`
			return
		elif status == 'Filled':
			# Wait until all the stocks are obtained
			if remaining == 0:
				log.info("Order complete: orderId: %d, instrument: %s, filled: %d, avgFillPrice=%.2f, lastFillPrice=%.2f" %
					 (orderId, instrument, filled, avgFillPrice, lastFillPrice))

				# Set commission to 0, avgFillPrice contains it 
				orderExecutionInfo = broker.OrderExecutionInfo(avgFillPrice, comission=0, dateTime=None)
				order.setExecuted(orderExecutionInfo)

				# Notify the listeners
				self.getOrderUpdatedEvent().emit(self, order)
			else:
				# And signal partial completions
				log.info("Partial order completion: orderId: %d, instrument: %s, filled: %d, remaining: %d, avgFillPrice=%.2f, lastFillPrice=%.2f" %
					 (orderId, instrument, filled, remaining, avgFillPrice, lastFillPrice))


	def getCash(self):
		"""Returns the amount of cash."""
		return self.__ibConnection.getCash()
	
	def setCash(self, cash):
		"""Setting cash on real broker account. Quite impossible :)"""
		raise Exception("Setting cash on a real broker account? Please visit your bank.")
	
	def placeOrder(self, order):
		"""Submits an order.

		:param order: The order to submit.
		:type order: :class:`Order`.
		"""

		instrument = order.getInstrument()

		# action: Identifies the side. 
		# Valid values are: BUY, SELL, SSHORT
		# XXX: SSHORT is not valid for some reason,
		# and SELL seems to work well with short orders.
		#action = "SSHORT"
		act = order.getAction()
		if act == broker.Order.Action.BUY:	action = "BUY"
		elif act == broker.Order.Action.SELL:	action = "SELL"
		elif act == broker.Order.Action.SELL_SHORT: action = "SELL"

		ot = order.getType()
		if ot == broker.Order.Type.MARKET:			orderType = "MKT"
		elif ot == broker.Order.Type.LIMIT:			orderType = "LMT"
		elif ot == broker.Order.Type.STOP:			orderType = "STP"
		elif ot == broker.Order.Type.STOP_LIMIT:	orderType = "STP LMT"
		else: raise Exception("Invalid orderType: %s!"% ot)

		if ot == broker.Order.Type.MARKET:
			lmtPrice     = 0
			auxPrice     = 0
		elif ot == broker.Order.Type.LIMIT:
			lmtPrice     = order.getPrice()
			auxPrice     = 0
		elif ot == broker.Order.Type.STOP:
			lmtPrice	 = 0
			auxPrice	 = order.getPrice()
		elif ot == broker.Order.Type.STOP_LIMIT:
			lmtPrice	 = order.getPrice() 
			auxPrice	 = order.getStopPrice() 

		goodTillDate = ""
		if order.getGoodTillCanceled():
			tif		 = "GTC"
		else:
			tif		 = "DAY"
		minQty		 = 0
		totalQty	 = order.getQuantity()

		orderId = self.__ibConnection.createOrder(instrument, action, lmtPrice, auxPrice, orderType, totalQty, minQty,
												  tif, goodTillDate, trailingPct=0, trailStopPrice=0, transmit=True, whatif=False)

		order.setOrderId(orderId)

		self.__orders[orderId] = order
		return orderId
	
	def start(self):
		pass

	def stop(self):
		pass

	def join(self):
		pass

	def stopDispatching(self):
		# If there are no more events in the barfeed, then there is nothing left for us to do since all processing took
		# place while processing barfeed events.
		return self.__barFeed.stopDispatching()

	def dispatch(self):
		# All events were already emitted while handling barfeed events.
		pass

	def createLongMarketOrder(self, instrument, quantity, goodTillCanceled=False):
		return(MarketOrder(self.__ibConnection, broker.Order.Action.BUY, instrument, quantity, goodTillCanceled))

	def createShortMarketOrder(self, instrument, quantity, goodTillCanceled=False):
		return(MarketOrder(self.__ibConnection, broker.Order.Action.SELL, instrument, quantity, goodTillCanceled))

	def createLongLimitOrder(self, instrument, price, quantity, goodTillCanceled=False): 
		return(LimitOrder(self.__ibConnection, broker.Order.Action.BUY, instrument, price, quantity, goodTillCanceled))

	def createShortLimitOrder(self, instrument, price, quantity, goodTillCanceled=False): 
		return(LimitOrder(self.__ibConnection, broker.Order.Action.SELL, instrument, price, quantity, goodTillCanceled))

	def createLongStopOrder(self, instrument, price, quantity, goodTillCanceled=False): 
		return(StopOrder(self.__ibConnection, broker.Order.Action.BUY, instrument, price, quantity, goodTillCanceled))

	def createShortStopOrder(self, instrument, price, quantity, goodTillCanceled=False): 
		return(StopOrder(self.__ibConnection, broker.Order.Action.SELL, instrument, price, quantity, goodTillCanceled))

	def createLongStopLimitOrder(self, instrument, limitPrice, stopPrice, quantity, goodTillCanceled=False): 
		return(StopLimitOrder(self.__ibConnection, broker.Order.Action.BUY, instrument, limitPrice, stopPrice, quantity, 
							  goodTillCanceled))

	def createShortStopLimitOrder(self, instrument, limitPrice, stopPrice, quantity, goodTillCanceled=False): 
		return(StopLimitOrder(self.__ibConnection, broker.Order.Action.SELL, instrument, limitPrice, stopPrice, quantity, 
							  goodTillCanceled))

# vim: noet:ci:pi:sts=0:sw=4:ts=4
