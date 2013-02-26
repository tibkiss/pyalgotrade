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

import collections

import broker

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib import finance
from matplotlib import dates

def _min(value1, value2):
	if value1 is None:
		return value2
	elif value2 is None:
		return value1
	else:
		return min(value1, value2)

def _max(value1, value2):
	if value1 is None:
		return value2
	elif value2 is None:
		return value1
	else:
		return max(value1, value2)

def _adjustXAxis(mplSubplots):
	minX = None
	maxX = None

	# Calculate min and max x values.
	for mplSubplot in mplSubplots:
		axis = mplSubplot.axis()
		minX = _min(minX, axis[0])
		maxX = _max(maxX, axis[1])

	for mplSubplot in mplSubplots:
		axis = mplSubplot.axis()
		axis = (minX, maxX, axis[2], axis[3])
		mplSubplot.axis(axis)

def _filter_datetimes(dateTimes, fromDate = None, toDate = None):
	class DateTimeFilter:
		def __init__(self, fromDate = None, toDate = None):
			self.__fromDate = fromDate
			self.__toDate = toDate

		def includeDateTime(self, dateTime):
			if self.__toDate and dateTime > self.__toDate:
				return False
			if self.__fromDate and dateTime < self.__fromDate:
				return False
			return True

	dateTimeFilter = DateTimeFilter(fromDate, toDate)
	return filter(lambda x: dateTimeFilter.includeDateTime(x), dateTimes)

class Series:
	def __init__(self):
		self.__values = {}

	def getColor(self):
		return None

	def addValue(self, dateTime, value):
		self.__values[dateTime] = value

	def getValue(self, dateTime):
		return self.__values.get(dateTime, None)

	def getMarker(self):
		raise NotImplementedError()

	def needColor(self):
		raise NotImplementedError()

	def plot(self, mplSubplot, dateTimes, color):
		values = []
		for dateTime in dateTimes:
			values.append(self.getValue(dateTime))
		mplSubplot.plot(dateTimes, values, color=color, marker=self.getMarker())

class BuyMarker(Series):
	def getColor(self):
		return 'g'

	def getMarker(self):
		return "^"

	def needColor(self):
		return True

class SellMarker(Series):
	def getColor(self):
		return 'r'

	def getMarker(self):
		return "v"

	def needColor(self):
		return True

class CustomMarker(Series):
	def needColor(self):
		return True

	def getMarker(self):
		return "o"

class LineMarker(Series):
	def needColor(self):
		return True

	def getMarker(self):
		return " "

class InstrumentMarker(Series):
	marker = " "

	def __init__(self):
		Series.__init__(self)
		self.__useCandleSticks = False
		self.__useAdjClose = False

	def needColor(self):
		return self.__useCandleSticks == False

	def getMarker(self):
		return InstrumentMarker.marker

	def setUseAdjClose(self, useAdjClose):
		self.__useAdjClose = useAdjClose

	def getValue(self, dateTime):
		# If not using candlesticks, the return the closing price.
		ret = Series.getValue(self, dateTime)
		if self.__useCandleSticks == False and ret != None:
			if self.__useAdjClose:
				ret = ret.getAdjClose()
			else:
				ret = ret.getClose()
		return ret

	def plot(self, mplSubplot, dateTimes, color):
		if self.__useCandleSticks:
			values = []
			for dateTime in dateTimes:
				bar = self.getValue(dateTime)
				if bar:
					values.append( (dates.date2num(dateTime), bar.getOpen(), bar.getClose(), bar.getHigh(), bar.getLow()) )
			finance.candlestick(mplSubplot, values, width=0.5, colorup='g', colordown='r',)
		else:
			Series.plot(self, mplSubplot, dateTimes, color)

class Subplot:
	""" """
	colors = ['b', 'c', 'm', 'y', 'k']

	def __init__(self):
		self.__series = {} # Series by name.
		self.__dataSeries = {} # Maps a pyalgotrade.dataseries.DataSeries to a Series.
		self.__nextColor = 0

	def __getColor(self, series):
		ret = series.getColor()
		if ret == None:
			ret = Subplot.colors[self.__nextColor % len(Subplot.colors)]
			self.__nextColor += 1
		return ret

	def isEmpty(self):
		return len(self.__series) == 0

	def addDataSeries(self, label, dataSeries):
		"""Adds a DataSeries to the subplot.

		:param label: A name for the DataSeries values.
		:type label: string.
		:param dataSeries: The DataSeries to add.
		:type dataSeries: :class:`pyalgotrade.dataseries.DataSeries`.
		"""
		self.__dataSeries[dataSeries] = self.getSeries(label)

	def addValuesFromDataSeries(self, dateTime):
		for ds, series in self.__dataSeries.iteritems():
			series.addValue(dateTime, ds.getValue())

	def getSeries(self, name, defaultClass=LineMarker):
		try:
			ret = self.__series[name]
		except KeyError:
			ret = defaultClass()
			self.__series[name] = ret
		return ret

	def getCustomMarksSeries(self, name):
		return self.getSeries(name, CustomMarker)

	def customizeSubplot(self, mplSubplot):
		# Don't scale the Y axis
		mplSubplot.yaxis.set_major_formatter(ticker.ScalarFormatter(useOffset=False))

	def plot(self, mplSubplot, dateTimes):
		for series in self.__series.values():
			color = None
			if series.needColor():
				color=self.__getColor(series)
			series.plot(mplSubplot, dateTimes, color)

		# Legend
		mplSubplot.legend(self.__series.keys(), shadow=True, loc="best")
		self.customizeSubplot(mplSubplot)

class InstrumentSubplot(Subplot):
	"""A Subplot responsible for plotting an instrument."""
	def __init__(self, instrument, plotBuySell):
		Subplot.__init__(self)
		self.__instrument = instrument
		self.__plotBuySell = plotBuySell
		self.__instrumentSeries = self.getSeries(instrument, InstrumentMarker)

	def setUseAdjClose(self, useAdjClose):
		self.__instrumentSeries.setUseAdjClose(useAdjClose)

	def onBars(self, bars):
		bar = bars.getBar(self.__instrument)
		if bar:
			dateTime = bars.getDateTime()
			self.__instrumentSeries.addValue(dateTime, bar)

	def onOrderUpdated(self, broker_, order):
		if self.__plotBuySell and order.isFilled() and order.getInstrument() == self.__instrument:
			action = order.getAction()
			execInfo = order.getExecutionInfo()
			if action in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
				self.getSeries("Buy", BuyMarker).addValue(execInfo.getDateTime(), execInfo.getPrice())
			elif action in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
				self.getSeries("Sell", SellMarker).addValue(execInfo.getDateTime(), execInfo.getPrice())

class StrategyPlotter:
	"""Class responsible for plotting a strategy execution.

	:param strat: The strategy to plot.
	:type strat: :class:`pyalgotrade.strategy.Strategy`.
	:param plotAllInstruments: Set to True to get a subplot for each instrument available.
	:type plotAllInstruments: boolean.
	:param plotBuySell: Set to True to get the buy/sell events plotted for each instrument available.
	:type plotBuySell: boolean.
	:param plotPortfolio: Set to True to get the portfolio value (shares + cash) plotted.
	:type plotPortfolio: boolean.
	"""

	def __init__(self, strat, plotAllInstruments=True, plotBuySell=True, plotPortfolio=True):
		self.__dateTimes = set()

		self.__plotAllInstruments = plotAllInstruments
		self.__plotBuySell = plotBuySell
		self.__barSubplots = {}
		self.__namedSubplots = collections.OrderedDict()
		self.__portfolioSubplot = None
		if plotPortfolio:
			self.__portfolioSubplot = Subplot()

		strat.getBarsProcessedEvent().subscribe(self.__onBarsProcessed)
		strat.getBroker().getOrderUpdatedEvent().subscribe(self.__onOrderUpdated)

	def __checkCreateInstrumentSubplot(self, instrument):
		if instrument not in self.__barSubplots:
			self.getInstrumentSubplot(instrument)

	def __onBarsProcessed(self, strat, bars):
		dateTime = bars.getDateTime()
		self.__dateTimes.add(dateTime)

		if self.__plotAllInstruments:
			for instrument in bars.getInstruments():
				self.__checkCreateInstrumentSubplot(instrument)

		# Notify named subplots.
		for subplot in self.__namedSubplots.values():
			subplot.addValuesFromDataSeries(dateTime)

		# Notify bar subplots.
		for subplot in self.__barSubplots.values():
			subplot.onBars(bars)
			subplot.addValuesFromDataSeries(dateTime)

		# Feed the portfolio evolution subplot.
		if self.__portfolioSubplot:
			self.__portfolioSubplot.getSeries("Portfolio").addValue(dateTime, strat.getBroker().getEquity())
			# This is in case additional dataseries were added to the portfolio subplot.
			self.__portfolioSubplot.addValuesFromDataSeries(dateTime)

	def __onOrderUpdated(self, broker_, order):
		# Notify BarSubplots
		for subplot in self.__barSubplots.values():
			subplot.onOrderUpdated(broker_, order)

	def getInstrumentSubplot(self, instrument):
		"""Returns the InstrumentSubplot for a given instrument

		:rtype: :class:`InstrumentSubplot`.
		"""
		try:
			ret = self.__barSubplots[instrument]
		except KeyError:
			ret = InstrumentSubplot(instrument, self.__plotBuySell)
			self.__barSubplots[instrument] = ret
		return ret

	def getOrCreateSubplot(self, name):
		"""Returns a Subplot by name. If the subplot doesn't exist, it gets created.

		:param name: The name of the Subplot to get or create.
		:type name: string.
		:rtype: :class:`Subplot`.
		"""
		try:
			ret = self.__namedSubplots[name]
		except KeyError:
			ret = Subplot()
			self.__namedSubplots[name] = ret
		return ret

	def getPortfolioSubplot(self):
		"""Returns the subplot where the portfolio values get plotted.

		:rtype: :class:`Subplot`.
		"""
		return self.__portfolioSubplot

	def plot(self, fromDateTime = None, toDateTime = None):
		"""Plots the strategy execution. Must be called after running the strategy.

		:param fromDateTime: An optional starting datetime.datetime. Everything before it won't get plotted.
		:type fromDateTime: datetime.datetime
		:param toDateTime: An optional ending datetime.datetime. Everything after it won't get plotted.
		:type toDateTime: datetime.datetime
		"""

		# dateTimes = [dateTime for dateTime in self.__dateTimes]
		dateTimes = _filter_datetimes(self.__dateTimes, fromDateTime, toDateTime)
		dateTimes.sort()

		subplots = []
		subplots.extend(self.__barSubplots.values())
		subplots.extend(self.__namedSubplots.values())
		if self.__portfolioSubplot != None:
			subplots.append(self.__portfolioSubplot)

		# Build each subplot.
		fig = plt.figure()
		mplSubplots = []
		subplotIndex = 0
		for subplot in subplots:
			if not subplot.isEmpty():
				mplSubplot = fig.add_subplot(len(subplots), 1, subplotIndex + 1)
				mplSubplots.append(mplSubplot)
				subplot.plot(mplSubplot, dateTimes)
				mplSubplot.grid(True)
				subplotIndex += 1

		_adjustXAxis(mplSubplots)

		# Display
		plt.show()

