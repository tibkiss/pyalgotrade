# PyAlgoTrade
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

"""
.. moduleauthor:: Tibor Kiss <tibor.kiss@gmail.com>
"""
from pyalgotrade.bar import Bars
from pyalgotrade.barfeed import csvfeed, BarFeed, Frequency
from pyalgotrade.providers.interactivebrokers import ibbar

import pytz
import datetime
from threading import Lock

######################################################################
## Interactive Brokers CSV parser
# Each bar must be on its own line and fields must be separated by comma (,).
#
# Bars Format:
# Date,Open,High,Low,Close,Volume,Trade Count,WAP,Has Gaps
#
# The csv Date column must have the following format: YYYYMMDD  hh:mm:ss


class RowParser(csvfeed.RowParser):
    def __init__(self, zone = pytz.UTC):
        self.__zone = zone

    def __parseDate(self, dateString, simpleParser=True):
        ret = None
        if simpleParser:
            (dt, tm) = dateString.split(" ")
            (yr, mt, dt) = dt.split("-")
            (hr, mn, sc) = tm.split(":")

            ret = datetime.datetime(int(yr), int(mt), int(dt), int(hr), int(mn), int(sc), tzinfo=self.__zone)
        else:
            ret = self.__zone.localize(datetime.datetime.strptime(dateString, "%Y-%m-%d %H:%M:%S"))

        return ret

    def getFieldNames(self):
        # It is expected for the first row to have the field names.
        return None

    def getDelimiter(self):
        return ","

    def parseBar(self, csvRowDict):
        date = self.__parseDate(csvRowDict["Date"])
        close = float(csvRowDict["Close"])
        open_ = float(csvRowDict["Open"])
        high = float(csvRowDict["High"])
        low = float(csvRowDict["Low"])
        volume = int(csvRowDict["Volume"])
        tradeCnt = int(csvRowDict["TradeCount"])
        VWAP = float(csvRowDict["VWAP"])
        # hasGaps = bool(csvRowDict["HasGaps"] == "True")

        return ibbar.Bar(date, open_, high, low, close, volume, VWAP, tradeCnt)

class CSVFeed(csvfeed.BarFeed):
    """A :class:`pyalgotrade.barfeed.BarFeed` that loads bars from a CSV file downloaded from IB TWS"""
    def __init__(self):
        csvfeed.BarFeed.__init__(self, Frequency.MINUTE)

    def addBarsFromCSV(self, instrument, path, timezone = pytz.utc):
        """Loads bars for a given instrument from a CSV formatted file.
        The instrument gets registered in the bar feed.

        :param instrument: Instrument identifier.
        :type instrument: string.
        :param path: The path to the file.
        :type path: string.
        :param timezone: The timezone for bars. 0 if bar dates are in UTC.
        :type timezone: int.
        """
        rowParser = RowParser(timezone)
        csvfeed.BarFeed.addBarsFromCSV(self, instrument, path, rowParser)


class LiveFeed(BarFeed):
    def __init__(self, ibConnection, timezone=pytz.utc, barsToInject=None):
        BarFeed.__init__(self, Frequency.SECOND)

        # The zone specifies the offset from Coordinated Universal Time (UTC)
        self.__zone = timezone

        # Connection to the IB's TWS
        self.__ibConnection = ibConnection

        self.__newBarsEventLock = Lock()
        self.__running = True

        self.__barsToInject = barsToInject

    def start(self):
        pass

    def stop(self):
        self.__running = False

    def join(self):
        pass

    def stopDispatching(self):
        return not self.__running

    def dispatch(self):
        # IB Live feed's dispatch functionality is implemented in onIBBar() method.
        # Here we only deal with the injectable bars defined by the user
        while self.__barsToInject:
            barDict = self.__barsToInject[0]
            for instr in barDict:
                barDict_dt = self.__barsToInject[0][instr].getDateTime()

                if barDict_dt <= datetime.datetime.now(tz=barDict_dt.tzinfo):
                    barDictToEmit = self.__barsToInject.pop(0)
                    with self.__newBarsEventLock:
                        barsToEmit = Bars(barDictToEmit)
                        self.getNewBarsEvent().emit(barsToEmit)
        return

    def subscribeRealtimeBars(self, instrument, useRTH_=0):
        self.__ibConnection.subscribeRealtimeBars(instrument, self.onIBBar, useRTH=useRTH_)
        self.registerInstrument(instrument)

    def unsubscribeRealtimeBars(self, instrument):
        self.__ibConnection.unsubscribeRealtimeBars(instrument, self.onIBBar)
        # XXX: Deregistering instrument is not yet possible, missing from BarFeed

    def subscribeMarketBars(self, instrument):
        self.__ibConnection.subscribeMarketBars(instrument, self.onIBBar)
        self.registerInstrument(instrument)

    def unsubscribeMarketBars(self, instrument):
        self.__ibConnection.unsubscribeMarketBars(instrument, self.onIBBar)

    def onIBBar(self, instrumentBar):
        instrument, bar = instrumentBar
        with self.__newBarsEventLock:
            bars = Bars({instrument: bar})
            self.getNewBarsEvent().emit(bars)

# vim: noet:ci:pi:sts=0:sw=4:ts=4
