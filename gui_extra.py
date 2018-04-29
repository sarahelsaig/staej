from gi.repository import Gtk


def replace_widget(old, new):
    parent= old.get_parent()

    props= {}
    for key in Gtk.ContainerClass.list_child_properties(type(parent)):
        props[key.name]= parent.child_get_property(old, key.name)

    parent.remove(old)
    parent.add(new)

    for name, value in props.iteritems():
        parent.child_set_property(new, name, value)