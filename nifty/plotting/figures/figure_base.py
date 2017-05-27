# -*- coding: utf-8 -*-

import abc

from nifty.plotting.plotly_wrapper import PlotlyWrapper


class FigureBase(PlotlyWrapper):
    def __init__(self, title, width, height):
        self.title = title
        self.width = width
        self.height = height

    @abc.abstractmethod
    def at(self):
        raise NotImplementedError

    @abc.abstractmethod
    def to_plotly(self):
        raise NotImplementedError
