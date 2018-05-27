from gi.repository import GObject

#import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas

from mpl_toolkits.mplot3d import Axes3D

class MatplotlibDrawingArea (FigureCanvas) :
    __highlight_point = -1

    def __init__(self, figure):
        self.figure = figure
        FigureCanvas.__init__(self, self.figure)

    @GObject.Property(type=int)
    def highlight_point(self): return self.__highlight_point

    @highlight_point.setter
    def highlight_point(self, value): self.__highlight_point = -1 if value is None or value < 0 else value

    def pack_into(self, container):
        container.pack_start(child=self, expand=True, fill=True, padding=0)
        return self


class TimeLinearPlot(MatplotlibDrawingArea):
    def __init__(self, step, show_legend = True, **series):
        self.axis_y = dict()
        # collect valid series
        y = list()
        names = list()
        for name in series:
            if series[name] and series[name].__iter__:
                self.axis_y[name] = series[name]
                y.append(series[name])
                names.append(name)

        length = max(map(len, y))
        figure = Figure()
        self.subplot = figure.add_subplot(1, 1, 1)
        self.axis_x = numpy.arange(0.0, step * length, step)

        if show_legend :
            self.subplot.legend(names)

        MatplotlibDrawingArea.__init__(self, figure)


class TrajectoryPlot(MatplotlibDrawingArea):
    __highlight_section = (0,0)

    def __init__(self, *values):
        self.figure = Figure()
        self.axes = list()
        self.lines = dict()
        self.__data = dict()
        self.__highlight_points = dict()
        self.__highlight_sections = dict()

        self.addSubplots(*values)
        MatplotlibDrawingArea.__init__(self, self.figure)
        for subplot in self.axes :
            Axes3D.mouse_init(subplot)

        self.connect('notify::highlight-point', self.updateHighlightPoint)

    @property
    def highlight_section(self):
        return self.__highlight_section

    @highlight_section.setter
    def highlight_section(self, value):
        try :
            self.__highlight_section = (value[0], value[1])
        except IndexError:
            self.__highlight_section = (0, value[0] if value else 0)
        except:
            self.__highlight_section = (0, value or 0)
        #print("HIGHLIGHT SECTION:", self.__highlight_section)

        for subplot in self.axes:
            x, y, z = [a[self.__highlight_section[0]:self.__highlight_section[1]] for a in self.__data[subplot]]
            if subplot in self.__highlight_sections :
                highlight = self.__highlight_sections[subplot][0]
                highlight.set_xdata(x)
                highlight.set_ydata(y)
                highlight.set_3d_properties(z)
            else:
                self.__highlight_sections[subplot] = subplot.plot(x, y, z)


    def addSubplots(self, *values):
        if len(values) == 0: return

        section_count = 3
        has_title = False
        if isinstance(values[0], str):
            section_count = 4
            has_title = True

        count = len(values) // section_count
        for i in range(count) :
            until = i * section_count + section_count
            x, y, z = values[until - 3 : until]
            subplot = self.figure.add_subplot(1, count, i + 1, projection='3d')
            self.axes.append(subplot)
            self.lines[subplot] = subplot.plot(x, y, z)
            self.__data[subplot] = (x, y, z)
            if has_title: subplot.set_title(values[i * section_count])

    def clear(self):
        self.figure.clear()
        self.axes = list()
        self.lines = dict()
        self.__data = dict()
        self.__highlight_points = dict()
        self.__highlight_sections = dict()

    do_embed = True
    def updateHighlightPoint(self, *dontcare):
        i = self.highlight_point
        for subplot in self.axes:
            x, y, z = [x[i] for x in self.__data[subplot]] # get coordinates of each subplot
            if subplot in self.__highlight_points :
                highlight = self.__highlight_points[subplot][0]
                highlight.set_xdata(x)
                highlight.set_ydata(y)
                highlight.set_3d_properties(z)
            else :
                self.__highlight_points[subplot] = subplot.plot([x], [y], [z], 'ro')

        from IPython import embed
        #if self.do_embed: embed()
        #for x in self.__highlight_points: x.remove()


