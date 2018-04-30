from gi.repository import GObject, Gtk


class GNotifier(GObject.Object) :
    """
    Base class for GObject based ViewModel.
    Provides methods to register GObject properties for MVVM style automatic two-way updates.
    """

    widget_types = dict()

    def __updateFromValue(self, value, gtypespec, *args):
        if isinstance(gtypespec, GObject.GParamSpec) :
            name = gtypespec.name
            type_name = gtypespec.value_type.name
            if type_name == 'gint' :
                value = int(value)
            elif type_name == 'gdouble':
                value = float(value)
            #else: type_name == 'gchararray':
        else :
            name = gtypespec

        self.set_property(name, value)

    def register(self, name, handler_or_widget, default_value = None, set_converter = None, get_converter = None):
        widget = None
        update = handler_or_widget
        if isinstance(handler_or_widget, Gtk.Widget) :
            widget = handler_or_widget
            update = None

        get_value = lambda : self.get_property(name)
        if set_converter is not None:
            get_value = lambda : set_converter(self.get_property(name))

        if widget :
            if isinstance(widget, Gtk.Label):
                update = lambda value : widget.set_label(value)
            elif isinstance(widget, Gtk.Entry):
                update = lambda value : widget.set_text(value)
                if get_converter is None :
                    widget_handler = lambda entry, gtypespec = None : self.__updateFromValue(entry.get_text(), gtypespec or name)
                else :
                    widget_handler = lambda entry, gtypespec = None: self.__updateFromValue(get_converter(entry.get_text()), gtypespec or name)
                widget.connect('changed', widget_handler)
            elif isinstance(widget, Gtk.Range):
                update = lambda value : widget.set_value(value)
                if get_converter is None :
                    widget_handler = lambda range, *args : self.set_property(name, range.get_value())
                else :
                    widget_handler = lambda range, *args : self.set_property(name, get_converter(range.get_value()))
                widget.connect('change-value', widget_handler)
            else :
                for t in self.widget_types : # look up additional handlers, signal_handler is (sender, gtypespec) => value
                    if (isinstance(widget, t)) :
                        if len(self.widget_types[t]) < 3:
                            self.widget_types[t] = list(self.widget_types[t]) + [None, None]
                        (update, signal_name, signal_handler) = self.widget_types[t][:3]
                        if signal_name and signal_handler:
                            if get_converter is None :
                                widget_handler = lambda sender, gtypespec : self.__updateFromValue(
                                    signal_handler(sender, gtypespec), gtypespec)
                            else :
                                widget_handler = lambda sender, gtypespec : self.__updateFromValue(
                                    get_converter(signal_handler(sender, gtypespec)), gtypespec)

                            widget.connect(signal_name, widget_handler)
                        break
                else :
                    raise NotImplementedError("Only [Label, Entry] are supported at this time.")

        if update is not None :
            self.connect('notify::' + name.replace('_', '-'), lambda *args : update(get_value()))

