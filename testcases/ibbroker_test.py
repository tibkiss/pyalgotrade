# PyAlgoTrade
#
# Copyright 2011 Gabriel Martin Becedillas Ruiz
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

"""
.. moduleauthor:: Tibor Kiss <tibor.kiss@gmail.com>
"""

import pytest
import unittest
import time, datetime

from pyalgotrade.providers.interactivebrokers.ibconnection import Connection
from pyalgotrade.providers.interactivebrokers.ibbar import Bar
from pyalgotrade.providers.interactivebrokers.ibfeed import LiveFeed
from pyalgotrade.providers.interactivebrokers.ibbroker import FlatRateCommission
from pyalgotrade.providers.interactivebrokers.ibbroker import Order, MarketOrder, LimitOrder
from pyalgotrade.providers.interactivebrokers.ibbroker import StopOrder, StopLimitOrder, Broker
from ib_testeclientsocket import TestEClientSocket


class IBBrokerTestCase(unittest.TestCase):
    def setUp(self):
        self.__testTWS = TestEClientSocket(self)
        self.__conn = Connection(eClientSocket=self.__testTWS, accountCode='DU123456')
        # link back the ib connection to testTWS
        self.__testTWS.setIBConnection(self.__conn)

        self.__feed = LiveFeed(self.__conn)
        self.__broker = Broker(self.__feed, self.__conn)

    def testFlatRateCommission(self):
        # US API Directed Orders (example from IB Website):
        # 100 Shares @ USD 25 Share Price = USD 1.30
        # 700 Shares @ USD 25 Share Price = USD 8.10
        comm = FlatRateCommission()
        self.assertEqual(comm.calculate(order=None, price=25, quantity=100), 1.30)
        self.assertEqual(comm.calculate(order=None, price=25, quantity=700), 8.10)

    def testCash(self):
        # Should return the predefined value from ib_testeclientsocket
        cash = self.__broker.getCash()
        self.assertEqual(cash, 28989.07)

        # Setting the cash should not be possible
        self.assertRaises(Exception, self.__broker.setCash, 420)

    def __validateOrderEntry(self, instrument, orderId, orderType, action, auxPrice, lmtPrice, quantity,
                             goodTillCanceled):
        self.assertEqual(instrument, self.__testTWS.orderContract.m_symbol)
        self.assertEqual(orderId, self.__testTWS.orderId)
        self.assertEqual(0, self.__testTWS.order.m_minQuantity)
        self.assertEqual(quantity, self.__testTWS.order.m_totalQuantity)
        self.assertEqual(auxPrice, self.__testTWS.order.m_auxPrice)
        self.assertEqual(lmtPrice, self.__testTWS.order.m_lmtPrice)
        if goodTillCanceled:
            self.assertEqual('GTC', self.__testTWS.order.m_tif)
        else:
            self.assertEqual('DAY', self.__testTWS.order.m_tif)
        self.assertEqual(orderType, self.__testTWS.order.m_orderType)
        self.assertEqual(action, self.__testTWS.order.m_action)

    def __validateOrderCancel(self):
        self.assertEqual(None, self.__testTWS.order)
        self.assertEqual(None, self.__testTWS.orderId)
        self.assertEqual(None, self.__testTWS.orderContract)

    def testMarketOrders(self):
        instrument1 = 'XMX'
        instrument2 = 'XMY'
        quantity1 = 12
        quantity2 = 22

        for gtc in (True, False):
            longMarketOrder = self.__broker.createLongMarketOrder(instrument=instrument1,
                                                                  quantity=quantity1, goodTillCanceled=gtc)
            shortMarketOrder = self.__broker.createShortMarketOrder(instrument=instrument2, quantity=quantity2,
                                                                    goodTillCanceled=gtc)

            # Issue the Order
            orderIdLong = self.__broker.placeOrder(longMarketOrder)
            self.__validateOrderEntry(instrument=instrument1, orderId=orderIdLong, orderType='MKT', action='BUY',
                                      auxPrice=0, lmtPrice=0, quantity=quantity1, goodTillCanceled=gtc)

            # Try to cancel it
            longMarketOrder.cancel()
            self.__validateOrderCancel()

            orderIdShort = self.__broker.placeOrder(shortMarketOrder)
            self.__validateOrderEntry(instrument=instrument2, orderId=orderIdShort, orderType='MKT', action='SELL',
                                      auxPrice=0, lmtPrice=0, quantity=quantity2, goodTillCanceled=gtc)

            shortMarketOrder.cancel()
            self.__validateOrderCancel()

            self.assertNotEqual(orderIdLong, orderIdShort)

    def testLimitOrders(self):
        instrument1 = 'XLX'
        instrument2 = 'YLY'
        quantity1 = 10
        quantity2 = 9
        price1 = 4.20
        price2 = 5.20
        for gtc in (True, False):
            longLimitOrder = self.__broker.createLongLimitOrder(instrument=instrument1, price=price1,
                                                                quantity=quantity1,
                                                                goodTillCanceled=gtc)
            shortLimitOrder = self.__broker.createShortLimitOrder(instrument=instrument2, price=price2,
                                                                  quantity=quantity2,
                                                                  goodTillCanceled=gtc)

            # Issue the Order
            orderIdLong = self.__broker.placeOrder(longLimitOrder)
            self.__validateOrderEntry(instrument=instrument1, orderId=orderIdLong, orderType='LMT', action='BUY',
                                      auxPrice=0, lmtPrice=price1, quantity=quantity1, goodTillCanceled=gtc)

            # Try to cancel it
            longLimitOrder.cancel()
            self.__validateOrderCancel()

            orderIdShort = self.__broker.placeOrder(shortLimitOrder)
            self.__validateOrderEntry(instrument=instrument2, orderId=orderIdShort, orderType='LMT', action='SELL',
                                      auxPrice=0, lmtPrice=price2, quantity=quantity2, goodTillCanceled=gtc)

            shortLimitOrder.cancel()
            self.__validateOrderCancel()

            self.assertNotEqual(orderIdLong, orderIdShort)

    def testStopOrders(self):
        instrument1 = 'XSX'
        instrument2 = 'YSY'
        quantity1 = 54
        quantity2 = 91
        price1 = 511.4
        price2 = 20
        for gtc in (True, False):
            longStopOrder = self.__broker.createLongStopOrder(instrument=instrument1, price=price1,
                                                              quantity=quantity1, goodTillCanceled=gtc)
            shortStopOrder = self.__broker.createShortStopOrder(instrument=instrument2, price=price2,
                                                                quantity=quantity2, goodTillCanceled=gtc)

            # Issue the Order
            orderIdLong = self.__broker.placeOrder(longStopOrder)
            self.__validateOrderEntry(instrument=instrument1, orderId=orderIdLong, orderType='STP', action='BUY',
                                      auxPrice=price1, lmtPrice=0, quantity=quantity1, goodTillCanceled=gtc)

            # Try to cancel it
            longStopOrder.cancel()
            self.__validateOrderCancel()

            orderIdShort = self.__broker.placeOrder(shortStopOrder)
            self.__validateOrderEntry(instrument=instrument2, orderId=orderIdShort, orderType='STP', action='SELL',
                                      auxPrice=price2, lmtPrice=0, quantity=quantity2, goodTillCanceled=gtc)

            shortStopOrder.cancel()
            self.__validateOrderCancel()

            self.assertNotEqual(orderIdLong, orderIdShort)

    def testStopLimitOrders(self):
        instrument1 = 'SLX'
        instrument2 = 'SLY'
        quantity1 = 7
        quantity2 = 5
        lmtPrice1 = 3.1415926535  # Long SL Order: stopPrice < lmtPrice
        stopPrice1 = 3.1
        lmtPrice2 = 1.61803399  # Short SL Order: lmtPrice < stopPrice
        stopPrice2 = 1.6
        for gtc in (True, False):
            longStopLimitOrder = self.__broker.createLongStopLimitOrder(instrument=instrument1,
                                                                        limitPrice=lmtPrice1, stopPrice=stopPrice1,
                                                                        quantity=quantity1, goodTillCanceled=gtc)
            shortStopLimitOrder = self.__broker.createShortStopLimitOrder(instrument=instrument2,
                                                                          limitPrice=lmtPrice2, stopPrice=stopPrice2,
                                                                          quantity=quantity2, goodTillCanceled=gtc)

            # Issue the Order
            orderIdLong = self.__broker.placeOrder(longStopLimitOrder)
            self.__validateOrderEntry(instrument=instrument1, orderId=orderIdLong, orderType='STP LMT', action='BUY',
                                      auxPrice=stopPrice1, lmtPrice=lmtPrice1, quantity=quantity1, goodTillCanceled=gtc)

            # Try to cancel it
            longStopLimitOrder.cancel()
            self.__validateOrderCancel()

            orderIdShort = self.__broker.placeOrder(shortStopLimitOrder)
            self.__validateOrderEntry(instrument=instrument2, orderId=orderIdShort, orderType='STP LMT', action='SELL',
                                      auxPrice=stopPrice2, lmtPrice=lmtPrice2, quantity=quantity2, goodTillCanceled=gtc)

            shortStopLimitOrder.cancel()
            self.__validateOrderCancel()

            self.assertNotEqual(orderIdLong, orderIdShort)


def getTestCases():
    ret = []
    ret.append(IBBrokerTestCase("testFlatRateCommission"))
    ret.append(IBBrokerTestCase("testMarketOrders"))
    ret.append(IBBrokerTestCase("testLimitOrders"))
    ret.append(IBBrokerTestCase("testStopOrders"))
    ret.append(IBBrokerTestCase("testStopLimitOrders"))
    return ret

# vim: noet:ci:pi:sts=0:sw=4:ts=4
