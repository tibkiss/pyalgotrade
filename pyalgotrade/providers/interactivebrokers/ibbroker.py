# PyAlgoTrade
#
# Related materials
# Interactive Brokers API:      http://www.interactivebrokers.com/en/software/api/api.htm
# IbPy: http://code.google.com/p/ibpy/
#
# Copyright 2012 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
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
    Value                    Flat Rate              Minimum Per Order       Maximum Per Order
    < = 500 shares  $0.013/share            USD 1.30                0.5% of trade value
    > 500 shares    $0.008/share            USD 1.30                0.5% of trade value
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

        log.debug("FlatRate commission: price=%.2f, quantity=%d minPerOrder=%.2f, maxPerOrder=%.4f, flatRate=%.4f  => commission=%.2f" %
                          (price, quantity, minPerOrder, maxPerOrder, flatRate, commission))

        return commission

class CostPlusCommission(broker.Commission):
    """Cost Plus Commission
    """
    def calculate(self, order, price, qty):
        maxPerOrder=(price * qty) * 0.005

        if qty <= 300000:
            IB_Comm = qty * 0.0035
            ARCA_Fee = qty * 0.003
            NSCC_DTC_Fee = qty * 0.0002
            US_Transaction_Fee = qty * price * 0.0000174  # Only on sales
            NYSE_PassTru = IB_Comm * 0.000175
            FINRA_PassTru = IB_Comm * 0.00056
            FINRA_TradingFee = 0.000119 * qty  # Only on sales
        else:
            log.error("CostPlus commission for qty > 300000 is not implemented")
            return 0

        commission = IB_Comm + ARCA_Fee + NSCC_DTC_Fee +  NYSE_PassTru + FINRA_PassTru
        if order.getAction() in (Order.Action.SELL, Order.Action.SELL_SHORT):
            commission += US_Transaction_Fee + FINRA_TradingFee

        commission = min(maxPerOrder, commission)

        log.debug("CostPlus commission: price=%.2f, quantity=%d, maxPerOrder=%.4f  => commission=%.2f" %
                          (price, qty, maxPerOrder, commission))

        return commission

######################################################################
## Orders

class Order(broker.Order):
    def __init__(self, ibConnection, type_, action, instrument, quantity, goodTillCanceled=False):
        broker.Order.__init__(self, type_, action, instrument, quantity)
        self.__ibConnection = ibConnection
        self.__goodTillCanceled = goodTillCanceled
        self.__orderId = None

    def setOrderId(self, orderId):
        self.__orderId = orderId

    def getOrderId(self):
        return self.__orderId

    def getGoodTillCanceled(self):
        return self.__goodTillCanceled

    def setGoodTillCanceled(self, goodTillCanceled):
        self.__goodTillCanceled = goodTillCanceled

class MarketOrder(Order):
    def __init__(self, ibConnection, action, instrument, quantity, goodTillCanceled=False):
        Order.__init__(self, ibConnection, Order.Type.MARKET, action, instrument, quantity, goodTillCanceled)

class LimitOrder(Order):
    def __init__(self, ibConnection, action, instrument, limitPrice, quantity, goodTillCanceled=False):
        Order.__init__(self, ibConnection, Order.Type.LIMIT, action, instrument, quantity, goodTillCanceled)
        self.__limitPrice = limitPrice

    def getLimitPrice(self):
        """Returns the limit price."""
        return self.__limitPrice

    def setLimitPrice(self, limitPrice):
        """Updates the limit price."""
        self.__limitPrice = limitPrice
        self.setDirty(True)

class StopOrder(Order):
    def __init__(self, ibConnection, action, instrument, stopPrice, quantity, goodTillCanceled=False):
        Order.__init__(self, ibConnection, Order.Type.STOP, action, instrument, quantity, goodTillCanceled)
        self.__stopPrice = stopPrice

    def getStopPrice(self):
        """Returns the stop price."""
        return self.__stopPrice

    def setStopPrice(self, stopPrice):
        """Updates the stop price."""
        self.__stopPrice = stopPrice
        self.setDirty(True)

class StopLimitOrder(Order):
    def __init__(self, ibConnection, action, instrument, limitPrice, stopPrice, quantity, goodTillCanceled=False):
        Order.__init__(self, ibConnection, Order.Type.STOP_LIMIT, action, instrument, quantity, goodTillCanceled)
        self.__limitPrice = limitPrice
        self.__stopPrice = stopPrice
        self.__limitOrderActive = False # Set to true when the limit order is activated (stop price is hit)

    def getLimitPrice(self):
        """Returns the limit price."""
        return self.__limitPrice

    def setLimitPrice(self, limitPrice):
        """Updates the limit price."""
        self.__limitPrice = limitPrice
        self.setDirty(True)

    def getStopPrice(self):
        """Returns the stop price."""
        return self.__stopPrice

    def setStopPrice(self, stopPrice):
        """Updates the stop price."""
        self.__stopPrice = stopPrice
        self.setDirty(True)


######################################################################
## Broker

class Broker(broker.Broker):
    """Class responsible for forwarding orders to Interactive Brokers Gateway via TWS.

    :param ibConnection: Object responsible to forward requests to TWS.
    :type ibConnection: :class:`IBConnection`
    """
    def __init__(self, barFeed, ibConnection, commission=FlatRateCommission()):
        self.__ibConnection = ibConnection
        self.__barFeed          = barFeed

        # Query the server for available funds
        self.__cash = self.__ibConnection.getCash()

        # Subscribe for order updates from TWS
        self.__ibConnection.subscribeOrderUpdates(self.__orderUpdate)

        # Local buffer for Orders. Keys are the orderIds
        self.__orders = {}

        # Call the base's constructor
        broker.Broker.__init__(self, self.__cash, commission)

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
            order.setState(broker.Order.State.CANCELED)
            log.debug("Order canceled: orderId: %d, instrument: %s" % (orderId, instrument))

            # Notify the listeners
            self.getOrderUpdatedEvent().emit(self, order)
        elif status == 'PreSubmitted':
            # Skip, we do not have the corresponding state in :class:`broker.Order`
            return
        elif status == 'Filled':
            # Wait until all the stocks are obtained
            if remaining == 0:
                log.debug("Order %d complete. Instr: %s, cnt: %d, avgFillPrice=%.2f, lastFillPrice=%.2f" %
                         (orderId, instrument, filled, avgFillPrice, lastFillPrice))

                # Set commission to 0, the avgFillPrice returned by IB already has this number included (per share)
                commission = self.getCommission().calculate(order, avgFillPrice, filled)
                orderExecutionInfo = broker.OrderExecutionInfo(avgFillPrice, filled, commission, dateTime=None)
                order.setExecuted(orderExecutionInfo)

                # Notify the listeners
                self.getOrderUpdatedEvent().emit(self, order)
            else:
                # And signal partial completions
                log.debug("Order %d partially complete. Instr: %s, cnt: %d, remaining: %d, avgFillPrice=%.2f, lastFillPrice=%.2f" %
                         (orderId, instrument, filled, remaining, avgFillPrice, lastFillPrice))

    def getCash(self):
        """Returns the amount of cash."""
        return self.__ibConnection.getCash()

    def setCash(self, cash):
        """Setting cash on real broker account. Quite impossible :)"""
        raise Exception("Setting cash on a real broker account? Please visit your bank.")

    def getShares(self, instrument):
        return self.__ibConnection.getShares(instrument)

    def getEquity(self):
        return self.__ibConnection.getNetLiquidation()

    def getAvgCost(self, instrument):
        return self.__ibConnection.getAvgCost(instrument)

    def getTotalCost(self, instrument):
        return self.__ibConnection.getAvgCost(instrument) * self.__ibConnection.getShares(instrument)

    def getLeverage(self):
        return self.__ibConnection.getLeverage()

    def start(self):
        pass

    def stop(self):
        pass

    def join(self):
        pass

    def stopDispatching(self):
        # If there are no more events in the barfeed, then there is nothing left for us to do
        return self.__barFeed.stopDispatching()

    def dispatch(self):
        # All events were already emitted while handling barfeed events.
        pass

    def placeOrder(self, order):
        """Submits an order.

        :param order: The order to submit.
        :type order: :class:`Order`.
        """

        instrument = order.getInstrument()
        if order.getState() != Order.State.ACCEPTED:
            raise Exception("The order was already processed")

        # action: Identifies the side.
        # Valid values are: BUY, SELL, SSHORT
        # XXX: SSHORT is not valid for some reason,
        # and SELL seems to work well with short orders.
        #action = "SSHORT"
        act = order.getAction()
        if act == broker.Order.Action.BUY:          action = "BUY"
        elif act == broker.Order.Action.SELL:       action = "SELL"
        elif act == broker.Order.Action.SELL_SHORT: action = "SELL"

        ot = order.getType()
        if ot == broker.Order.Type.MARKET:          orderType = "MKT"
        elif ot == broker.Order.Type.LIMIT:         orderType = "LMT"
        elif ot == broker.Order.Type.STOP:          orderType = "STP"
        elif ot == broker.Order.Type.STOP_LIMIT:    orderType = "STP LMT"
        else: raise Exception("Invalid orderType: %s!"% ot)

        if ot == broker.Order.Type.MARKET:
            lmtPrice = 0
            auxPrice = 0
        elif ot == broker.Order.Type.LIMIT:
            lmtPrice = order.getLimitPrice()
            auxPrice = 0
        elif ot == broker.Order.Type.STOP:
            lmtPrice = 0
            auxPrice = order.getStopPrice()
        elif ot == broker.Order.Type.STOP_LIMIT:
            lmtPrice = order.getLimitPrice()
            auxPrice = order.getStopPrice()

        goodTillDate = ""
        tif = "GTC" if order.getGoodTillCanceled() else "DAY"
        minQty = 0
        totalQty = order.getQuantity()

        orderId_ = order.getOrderId()
        orderId_ = self.__ibConnection.createOrder(instrument, action, lmtPrice, auxPrice, orderType, totalQty, minQty,
                                                   tif, goodTillDate, trailingPct=0, trailStopPrice=0, transmit=True,
                                                   whatif=False, orderId=orderId_)

        order.setOrderId(orderId_)

        self.__orders[orderId_] = order
        return orderId_

    def createMarketOrder(self, action, instrument, quantity, onClose=False, goodTillCanceled=False):
        return MarketOrder(self.__ibConnection, action, instrument, quantity, goodTillCanceled)

    def createLimitOrder(self, action, instrument, limitPrice, quantity, goodTillCanceled=False):
        return LimitOrder(self.__ibConnection, action, instrument, limitPrice, quantity, goodTillCanceled)

    def createStopOrder(self, action, instrument, stopPrice, quantity, goodTillCanceled=False):
        return StopOrder(self.__ibConnection, action, instrument, stopPrice, quantity, goodTillCanceled)

    def createStopLimitOrder(self, action, instrument, stopPrice, limitPrice, quantity, goodTillCanceled=False):
        return StopLimitOrder(self.__ibConnection, action, instrument, limitPrice, stopPrice, quantity, goodTillCanceled)

    def cancelOrder(self, order):
        # Ask the broker to cancel the position
        if order.isFilled():
            raise Exception("Can't cancel order that has already been filled")
        if order.getOrderId() is None:
            raise Exception("Can't cancel order which was not submitted")

        self.__ibConnection.cancelOrder(order.getOrderId())

# vim: noet:ci:pi:sts=0:sw=4:ts=4
