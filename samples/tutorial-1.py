from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed

class MyStrategy(strategy.Strategy):
    def __init__(self, feed, instrument):
        strategy.Strategy.__init__(self, feed)
        self.__instrument = instrument

    def onBars(self, bars):
        bar = bars[self.__instrument]
        print "%s: %s" % (bar.getDateTime(), bar.getClose())

# Load the yahoo feed from the CSV file
feed = yahoofeed.Feed()
feed.addBarsFromCSV("orcl", "orcl-2000.csv")

# Evaluate the strategy with the feed's bars.
myStrategy = MyStrategy(feed, "orcl")
myStrategy.run()
