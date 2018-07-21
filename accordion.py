from gi.repository import Gtk


class Accordion :
    """
    A manager which turns a container widget with an alternating sequence of buttons and
    other widgets into an accordion.
    """

    def __init__(self, widget, add_end_padding):
        """
        Turns the selected widget into an accordion with any button direct descendant as
        headers for the widgets that follow.
        :param widget: The container that has the buttons and content widgets.
        :param add_end_padding: If true, an extra empty label will be appendded to the container to provide padding
        """

        self.widget = widget

        self.subscription = dict()
        self.first = None
        owner = None
        for child in widget :
            if isinstance(child, Gtk.Button) :  # header
                owner = child
                self.first = self.first or child
                self.subscription[owner] = list()
                continue
            if owner is not None :  # non-header at the beginning
                self.subscription[owner].append(child)

        for owner in tuple(self.subscription) :
            if not self.subscription[owner] :
                del self.subscription[owner]

        self.toggle_buttons = list()
        for owner in self.subscription :
            if isinstance(owner, Gtk.ToggleButton) :
                self.toggle_buttons.append(owner)
            owner.connect('clicked', self.on_header_click)

        if add_end_padding:
            label = Gtk.Label()
            label.set_css_name('accordion_end_padding')
            label.set_text('asd')
            widget.pack_end(label, True, True, 0)

        self.set(self.first, True)

    def set(self, button, is_active):
        for child in self.subscription[button] :
            child.show() if is_active else child.hide()

        # turn off others
        for owner in self.subscription:
            if owner == button :
                continue
            if owner in self.toggle_buttons :
                owner.set_active(False)
            for child in self.subscription[owner] :
                child.hide()

    def on_header_click(self, button):
        if button in self.toggle_buttons :
            is_active = button.get_active()
        else :
            is_active = not self.subscription[button][0].is_visible()
        return self.set(button, is_active)
