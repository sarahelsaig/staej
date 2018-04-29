import model
import model.database
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo
import gui_extra
import os
from peewee import fn
from video_player import VideoPlayer
from IPython import embed


DIR_CONFIG = 'dir_config'

secondsToMinutesStr = lambda s : "{:02d}:{:02d}".format(s // 60, s % 60)

Gst.FRAME = Gst.SECOND // 30


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