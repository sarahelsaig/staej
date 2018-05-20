from enum import Enum

import cairo

import gi
import gnotifier
from gi.repository import GObject, Gtk
from IPython import embed

COLORS = [
    [0.9569, 0.2627, 0.2118],
    [0.9137, 0.1176, 0.3882],
    [0.6118, 0.1529, 0.6902],
    [0.4039, 0.2275, 0.7176],
    [0.2471, 0.3176, 0.7098],
    [0.1294, 0.5882, 0.9529],
    [0.0118, 0.6627, 0.9569],
    [0.0000, 0.7373, 0.8314],
    [0.0000, 0.5882, 0.5333],
    [0.2980, 0.6863, 0.3137],
    [0.5451, 0.7647, 0.2902],
    [0.8039, 0.8627, 0.2235],
    [1.0000, 0.9216, 0.2314],
    [1.0000, 0.7569, 0.0275],
    [1.0000, 0.5961, 0.0000],
    [1.0000, 0.3412, 0.1333],
    [0.4745, 0.3333, 0.2824],
    [0.6196, 0.6196, 0.6196],
    [0.3765, 0.4902, 0.5451],
    ]

def restoreContext(f) :
    def wrapper (self, ctx, *args, **kwargs) :
        ctx.save()
        f(self, ctx, *args, **kwargs)
        ctx.restore()
    return wrapper

class DiagramType(Enum) :
    LINE = 1

class LiveDiagram(gnotifier.GNotifier):
    drawing_area = None
    diagram_type = DiagramType.LINE
    width = 0
    height = 0
    data = []

    def __init__(self, drawing_area, diagram_type = DiagramType.LINE):
        self.drawing_area = drawing_area
        self.diagram_type = diagram_type
        drawing_area.connect('draw', self.draw)

    def addSeries(self, series):
        self.data.append(series)

    @restoreContext
    def drawLineGraph(self, ctx, color_index):
        if len(self.data) == 0 : return

        color_index %= len(COLORS)
        ctx.set_source_rgb(COLORS[color_index][0], COLORS[color_index][1], COLORS[color_index][2])
        ctx.translate(0, color_index * 3)

        ctx.new_path()
        ctx.move_to(0, self.data[0])
        i = 0
        while i < len(self.data) :
            ctx.line_to(i * (self.width / len(self.data)), self.data[i])
            i += 1
        ctx.stroke()

    def draw(self, drawing_area, ctx):
        allocation = drawing_area.get_allocation()
        self.width = allocation.width
        self.height = allocation.height

        ctx.set_line_width(2)
        ctx.set_tolerance(0.1)

        if self.diagram_type == DiagramType.LINE :
            for i in range(len(self.data)) :
                self.drawLineGraph(ctx, i)
