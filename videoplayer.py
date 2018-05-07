import sys
from gi.repository import GObject, Gtk, Gst, GstVideo
from gnotifier import GNotifier


Gst.FRAME = Gst.SECOND // 30

def getXid(window) :
    if sys.platform == "win32":
        if not window.ensure_native():
            print("Error - video playback requires a native window")
        import ctypes
        ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
        ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
        gpointer = ctypes.pythonapi.PyCapsule_GetPointer(window.__gpointer__, None)
        gdkdll = ctypes.CDLL ("libgdk-3-0.dll")
        return gdkdll.gdk_win32_window_get_handle(gpointer)
    else:
        from gi.repository import GdkX11
        return window.get_xid()

class VideoPlayer(GNotifier) :
    __video_duration = 0
    __video_position = 0

    def __init__(self, **properties):
        GNotifier.__init__(self, **properties)

        self.playbin = Gst.ElementFactory.make('playbin', None)
        if not self.playbin :
            sys.stderr.write("'playbin' gstreamer plugin missing\n")
            sys.exit(1)

        self.pipeline = Gst.Pipeline()
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.onEOS)
        self.bus.connect('message::error', self.onVideoError)
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.onSyncMessage)
        self.pipeline.add(self.playbin)

    @GObject.Property(type=bool, default=False)
    def video_playing(self):
        return Gst.State.PLAYING in self.pipeline.get_state(10000)

    @video_playing.setter
    def video_playing(self, value):
        self.pipeline.set_state(Gst.State.PLAYING if value else Gst.State.PAUSED)

    @property
    def video_duration(self):
        success, duration = self.pipeline.query_duration(Gst.Format.TIME)
        if success and self.__video_duration != duration :
            self.__video_duration = duration
            # send signal
        return self.__video_duration

    @GObject.Property(type=GObject.TYPE_LONG)
    def video_position(self):
        success, position = self.pipeline.query_position(Gst.Format.TIME)
        if success and position != self.__video_position:
            print (position)
            self.__video_position = position
        return self.__video_position

    @video_position.setter
    def video_position(self, value):
        print (value)
        self.seek(value, Gst.Format.TIME)

    def load(self, path):
        uri = path if Gst.uri_is_valid(path) else Gst.filename_to_uri(path)
        self.playbin.set_property('uri', uri)
        self.play()
        self.pause()

    def playpause(self, *args):
        self.xid = getXid(self.video_player.get_property('window'))

        self.video_playing = not self.video_playing

    def play(self, *args):
        self.xid = getXid(self.video_player.get_property('window'))
        self.pipeline.set_state(Gst.State.PLAYING)

    def pause(self, *args):
        self.xid = getXid(self.video_player.get_property('window'))
        self.pipeline.set_state(Gst.State.PAUSED)

    def relativeSeek(self, button):
        offset = int(button.get_name().replace('seek:','')) * Gst.FRAME
        self.video_position += offset

    def seek(self, position, format = Gst.Format.TIME):
        return self.pipeline.seek_simple(
            format,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
            position)

    def onSyncMessage(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            print('prepare-window-handle')
            msg.src.set_window_handle(self.xid)

    def onEOS(self, bus, msg):
        print('onEOS(): seeking to start of video')
        self.pipeline.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            0
        )

    def onVideoError(self, bus, msg):
        print('onVideoError():', msg.parse_error())