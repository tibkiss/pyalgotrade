# PyAlgoTrade
#
# Copyright 2012 Gabriel Martin Becedillas Ruiz
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

import pyalgotrade.barfeed
from pyalgotrade.barfeed import csvfeed
from pyalgotrade import bar

import types
import datetime
import pytz

######################################################################
## IQFeed CSV parser - Based on ninjatraderfeed.py
# Each bar must be on its own line and fields must be separated by semicolon (,).
#
# Minute Bars Format:
# yyyyMMdd HHmmss,open price,high price,low price,close price,volume
#
# It is expected to have a header row in the file
def parse_datetime(dateTime, timezone):
    # Sample: 20081231 230600
    # This custom parsing works faster than:
    # datetime.datetime.strptime(dateTime, "%Y%m%d %H%M%S")
    year = int(dateTime[0:4])
    month = int(dateTime[4:6])
    day = int(dateTime[6:8])
    hour = int(dateTime[9:11])
    minute = int(dateTime[11:13])
    sec = int(dateTime[13:15])

    dt = datetime.datetime(year, month, day, hour, minute, sec, tzinfo=timezone)

    return dt

class Frequency:
    MINUTE = pyalgotrade.barfeed.Frequency.MINUTE

class RowParser(csvfeed.RowParser):
    def __init__(self, frequency, dailyBarTime, timezone = None):
        self.__frequency = frequency
        self.__dailyBarTime = dailyBarTime
        self.__timezone = timezone

    def __parseDateTime(self, dateTime):
        ret = None
        if self.__frequency == pyalgotrade.barfeed.Frequency.MINUTE:
            # The returned dates are localized if timezone was given
            ret = parse_datetime(dateTime, self.__timezone)
        else:
            assert(False)

        return ret

    def getFieldNames(self):
        # It is expected for the first row to have the field names.
        return None

    def getDelimiter(self):
        return ","

    def parseBar(self, csvRowDict):
        dateTime = self.__parseDateTime(csvRowDict["Date Time"])
        close = float(csvRowDict["Close"])
        open_ = float(csvRowDict["Open"])
        high = float(csvRowDict["High"])
        low = float(csvRowDict["Low"])
        volume = float(csvRowDict["Volume"])
        adjClose = close
        date_ = dateTime.date()

        return bar.Bar(dateTime, open_, high, low, close, volume, adjClose, date_)

class Feed(csvfeed.BarFeed):
    """A :class:`pyalgotrade.barfeed.csvfeed.BarFeed` that loads bars from CSV files exported from NinjaTrader.

    :param frequency: The frequency of the bars.
    :param timezone: The default timezone to use to localize bars. Check :mod:`pyalgotrade.marketsession`.
    :type timezone: A pytz timezone.

    .. note::

            Valid **frequency** parameter values are:

             * pyalgotrade.barfeed.Frequency.MINUTE
    """

    def __init__(self, frequency, timezone = pytz.utc):
        if type(timezone) == types.IntType:
            raise Exception("timezone as an int parameter is not supported anymore. Please use a pytz timezone instead.")

        csvfeed.BarFeed.__init__(self, frequency)
        self.__timezone = timezone

    def addBarsFromCSV(self, instrument, path, timezone = None):
        """Loads bars for a given instrument from a CSV formatted file.
        The instrument gets registered in the bar feed.

        :param instrument: Instrument identifier.
        :type instrument: string.
        :param path: The path to the file.
        :type path: string.
        :param timezone: The timezone to use to localize bars. Check :mod:`pyalgotrade.marketsession`.
        :type timezone: A pytz timezone.
        """

        if type(timezone) == types.IntType:
            raise Exception("timezone as an int parameter is not supported anymore. Please use a pytz timezone instead.")

        if timezone is None:
            timezone = self.__timezone

        rowParser = RowParser(self.getFrequency(), self.getDailyBarTime(), timezone)
        csvfeed.BarFeed.addBarsFromCSV(self, instrument, path, rowParser)
