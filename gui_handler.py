import sys
import model
import model.database
from gi.repository import GObject, Gst, Gtk
import gui_extra
import os
from peewee import fn

DIR_CONFIG = 'dir_config'

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo

secondsToMinutesStr = lambda s : "{:02d}:{:02d}".format(s // 60, s % 60)

Gst.FRAME = Gst.SECOND // 30

from IPython import embed

class VideoPlayer :
    def __init__(self):
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

    @property
    def video_playing(self):
        return Gst.State.PLAYING in self.pipeline.get_state(10000)

    @video_playing.setter
    def video_playing(self, value):
        self.pipeline.set_state(Gst.State.PLAYING if value else Gst.State.PAUSED)


    def load(self, path):
        uri = path if Gst.uri_is_valid(path) else Gst.filename_to_uri(path)
        self.playbin.set_property('uri', uri)
        self.play()
        self.pause()

    def playpause(self, *args):
        self.xid = self.video_player.get_property('window').get_xid()

        self.video_playing = not self.video_playing

    def play(self, *args):
        self.xid = self.video_player.get_property('window').get_xid()
        self.pipeline.set_state(Gst.State.PLAYING)

    def pause(self, *args):
        self.xid = self.video_player.get_property('window').get_xid()
        self.pipeline.set_state(Gst.State.PAUSED)

    def relativeSeek(self, button):
        success, position = self.pipeline.query_position(Gst.Format.TIME)
        if not success: return

        offset = int(button.get_name().replace('seek:','')) * Gst.FRAME
        self.seek(position + offset)

        #print (position, offset, (position + offset) // Gst.FRAME)
        success, position = self.pipeline.query_position(Gst.Format.TIME)
        #print (position, offset, position // Gst.FRAME)

        #embed()

    def seek(self, units, format = Gst.Format.TIME):
        return self.pipeline.seek_simple(
            format,
            Gst.SeekFlags.FLUSH, # | Gst.SeekFlags.ACCURATE,
            units)

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

class Handler (VideoPlayer):

    def __init__(self, glade_file, dir_config):
        VideoPlayer.__init__(self)

        # set up Glade builder
        builder = Gtk.Builder()
        self.glade_file = glade_file
        builder.add_from_file(glade_file)
        builder.connect_signals(self)
        self.builder = builder

        self.dir_config = dir_config

        # get elements by ID
        self.video_store = builder.get_object("video_store")
        self.kinematic_store = builder.get_object("kinematic_store")
        self.main_window = builder.get_object("main_window")
        self.label_task_name = builder.get_object("label_task_name")
        self.label_video_name = builder.get_object("label_video_name")
        self.label_video_length = builder.get_object("label_video_length")
        self.scale_video_position = builder.get_object("scale_video_position")
        self.video_player = builder.get_object("video_player")

        # get task list
        self.tasks = dict()
        for task in model.database.Task.select():
            self.tasks[task.id] = task.name

        # fill list view with video names
        root_iter = self.video_store.get_iter_first()
        video_store_tasks = dict()
        for task_id in self.tasks :
            video_store_tasks[task_id] = self.video_store.append(root_iter, [self.tasks[task_id], task_id, False])
        for video in model.database.Video.select():
            if video.file_name :
                self.video_store.append(video_store_tasks[video.task_id], [video.file_name, video.id, True])

        # set up video player
        #VideoPlayer.beforeShow(self)
        self.main_window.show_all()

    def onExit(self, *args):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit(*args)

    def onButtonPressed(self, button):
        print("Hello World!")

    def onVideoSelectionChanged(self, tree_selection):
        store, item = tree_selection.get_selected()
        name, id, selectable = store[item]
        if not selectable : return

        self.video = model.database.Video.get(id = id)

        self.updateVideo()


    def updateVideo(self, video = None):
        if video is None : video = self.video

        # fill in general part of Video Info
        self.task_name = self.tasks[self.video.task_id]
        self.video_name = self.video.file_name
        self.video_length = (model.database.Kinematic
                .select()
                .where(model.database.Kinematic.video_id == self.video.id)
                .select(fn.Max(model.database.Kinematic.frame))
                .scalar()
            )

        # physical location of the video file
        file_name = os.path.join(
            self.dir_config,
            'tasks',
            self.task_name,
            'video',
            self.video_name + '_capture1.avi')
        self.load(file_name)

    @property
    def task_name(self):
        return self._task_name

    @task_name.setter
    def task_name(self, value):
        self._task_name = value
        self.label_task_name.set_label(value)

    @property
    def video_name(self):
        return self._video_name

    @video_name.setter
    def video_name(self, value):
        self._video_name = value
        self.label_video_name.set_label(value)

    @property
    def video_length(self):
        return self._video_length

    @video_length.setter
    def video_length(self, value):
        self._video_length = value
        self.label_video_length.set_label(secondsToMinutesStr(value // 30))
        self.scale_video_position.set_adjustment(Gtk.Adjustment(1, 1, value, 1, 1, 0))



def start(config) :
    GObject.threads_init()
    Gst.init(None)

    model.database.connectFileDb(config)

    handler = Handler("gui.glade", config[DIR_CONFIG])
    return Gtk.main()