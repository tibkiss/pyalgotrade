#!/usr/bin/env python

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


from distutils.core import setup

setup(name='PyAlgoTrade',
        version='0.12',
        description='Python Algorithmic Trading',
        long_description='Python library for backtesting stock trading strategies.',
        author='Gabriel Martin Becedillas Ruiz',
        author_email='pyalgotrade@gmail.com',
        url='http://gbeced.github.com/pyalgotrade/',
        download_url='http://sourceforge.net/projects/pyalgotrade/files/0.12/PyAlgoTrade-0.12.tar.gz/download',
        packages=['pyalgotrade',
                'pyalgotrade.barfeed',
                'pyalgotrade.broker',
                'pyalgotrade.optimizer',
                'pyalgotrade.stratanalyzer',
                'pyalgotrade.strategy',
                'pyalgotrade.talibext',
                'pyalgotrade.technical',
                'pyalgotrade.tools',
                'pyalgotrade.utils',],
)
