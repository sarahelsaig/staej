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
COLORS_COUNT = len(COLORS)
COLORS_ORDER = [x + i for i in range(3) for x in [0,6,12,3,9,15]] + [18] # custom order for ore scattered colors

def getColors(amount = None, single = False):
    if amount is None : return COLORS
    amount %= COLORS_COUNT
    if single : return COLORS[COLORS_ORDER[amount]]
    return [COLORS[i] for i in COLORS_ORDER[:amount]]

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
    min = 0
    max = 100
    __data = []
    __vline = None

    def __init__(self, drawing_area, diagram_type = DiagramType.LINE):
        self.drawing_area = drawing_area
        self.diagram_type = diagram_type
        drawing_area.connect('draw', self.draw)

    @property
    def data(self): return self.__data

    @data.setter
    def data(self, value):
        self.__data = value
        if value is None or len(value) == 0  : return
        items = [ x for series in self.data for x in series ]
        if len(items) == 0: return

        self.min = min(0, *items)
        self.max = max(items)
        self.drawing_area.queue_draw()

    @property
    def vline(self): return self.__vline

    @vline.setter
    def vline(self, value):
        self.__vline = value
        self.drawing_area.queue_draw()


    @restoreContext
    def drawLineGraph(self, ctx, color_index):
        if len(self.data) <= color_index or len(self.data[color_index]) == 0 : return
        data = self.data[color_index]

        color = getColors(color_index, single=True)
        ctx.set_source_rgb(*color)

        trs = self.height / (self.max - self.min)
        ofs = self.min * trs

        ctx.new_path()
        ctx.move_to(0, self.height - (data[0] * trs - ofs))
        length = len(data)
        for i in range(length) :
            ctx.line_to(i * (self.width / length), self.height - (data[i] * trs - ofs))
        ctx.stroke()

    @restoreContext
    def drawLinePerc(self, ctx, x1=0, x2=1, y1=0, y2=1, line_width=1, rgb=(0, 0, 0), is_dash=False) :
        ctx.set_line_width(line_width)
        ctx.set_source_rgb(*rgb)
        if is_dash : ctx.set_dash([4,4], 0)
        ctx.new_path()
        ctx.move_to(x1 * self.width, y1 * self.height)
        ctx.line_to(x2 * self.width, y2 * self.height)
        ctx.stroke()

    def draw(self, drawing_area, ctx):
        allocation = drawing_area.get_allocation()
        self.width = allocation.width
        self.height = allocation.height

        ctx.set_line_width(2)
        ctx.set_tolerance(0.1)

        if self.diagram_type == DiagramType.LINE :
            if self.min == 0 :
                # line at the bottom
                self.drawLinePerc(ctx, y1=1, line_width=2)
            else :
                # min < 0, line at zero, so drawn at height * (1 - |min| / delta)
                y0 = 1 + self.min / (self.max - self.min)
                self.drawLinePerc(ctx, y1=y0, y2=y0, line_width=1)
            for i in range(len(self.data)) :
                self.drawLineGraph(ctx, i)

        if self.vline is not None :
            if self.vline < 0: self.vline += 1
            self.drawLinePerc(ctx, x1=self.vline, x2=self.vline, is_dash=True)

