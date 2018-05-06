import model
import model.database
from gi.repository import GObject, Gst, Gtk
import os
from peewee import fn
from videoplayer import VideoPlayer
from IPython import embed


DIR_CONFIG = 'dir_config'

secondsToMinutesStr = lambda s : "{:02d}:{:02d}".format(s // 60, s % 60)



class Handler (VideoPlayer):
    __task_name = ""
    __video_name = ""
    __video_length = 0
    __video_search = ""

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
        self.gesture_store = builder.get_object("gesture_store")
        self.main_window = builder.get_object("main_window")
        self.scale_video_position = builder.get_object("scale_video_position")
        self.video_player = builder.get_object("video_player")
        self.label_subject = builder.get_object("label_subject")

        # gui binding
        self.register("task_name", builder.get_object("label_task_name"))
        self.register("video_name", builder.get_object("label_video_name"))
        self.register("video_length", builder.get_object("label_video_length"),
                      set_converter=lambda value: secondsToMinutesStr(value // 30))
        self.register("video_position", self.scale_video_position)
        self.register("video_playing", builder.get_object("button_playpause").get_child(),
                      set_converter=lambda value: '||' if value else '|>')
        self.register("video_search", builder.get_object("entry_video_search"))

        # set up video store filter
        self.video_store.filter = self.video_store.filter_new()
        builder.get_object("treeview_video").set_model(self.video_store.filter)
        self.video_store.filter.set_visible_func(self.videoStoreFilter)

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

        # set up gesture dict
        self.gestures = dict()
        for x in model.database.Gesture.select():
            self.gestures[x.id] = x.description

        # set up video player
        self.main_window.show_all()


    @GObject.Property(type=str)
    def task_name(self): return self.__task_name

    @task_name.setter
    def task_name(self, value): self.__task_name = value

    @GObject.Property(type=str)
    def video_name(self): return self.__video_name

    @video_name.setter
    def video_name(self, value): self.__video_name = value

    @GObject.Property(type=int)
    def video_length(self): return self.__video_length

    @video_length.setter
    def video_length(self, value):
        self.__video_length = value
        self.scale_video_position.set_adjustment(Gtk.Adjustment(1, 1, value * Gst.FRAME, 1, 1, 0))

    @GObject.Property(type=str)
    def video_search(self): return self.__video_search

    @video_search.setter
    def video_search(self, value):
        self.__video_search = value.lower()
        self.video_store.filter.refilter()

    def onExit(self, *args):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit(*args)

    def onVideoSelectionChanged(self, tree_selection):
        store, item = tree_selection.get_selected()
        if not store or not item : return
        name, id, selectable = store[item]
        if not selectable : return

        self.video = model.database.Video.get(id = id)

        self.updateVideo()

    def onGestureSelectionChanged(self, tree_selection):
        store, item = tree_selection.get_selected()
        if not store or not item : return

        id, desc, start, end = store[item]
        if not (start <= self.video_position / Gst.FRAME <= end) :
            self.video_position = start * Gst.FRAME

    def videoStoreFilter(self, model, iter, user_data):
        query = self.video_search
        if not query or query == 'None' :
            return True

        print (model[iter][0].lower(), query, query in model[iter][0].lower())
        return query in model[iter][0].lower()


    def getGrs(self, score, dictionary):
        ret = None
        if dictionary: ret = dictionary.get(score)
        return ret or model.database.GRS[score]

    def updateVideo(self):
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

        # update the Gestures tab
        self.gesture_store.clear()
        for x in model.database.Transcript.select().where(model.database.Transcript.video_id == self.video.id).order_by(model.database.Transcript.start) :
            self.gesture_store.append([x.gesture_id, self.gestures[x.gesture_id], x.start, x.end])

        self.label_subject.set_markup('\n'.join([
                          '<b>Subject Code</b>: ' + self.video.file_name.rpartition('_')[2][0],
                          '<b>Trial</b>: ' + self.video.file_name[-1],
                          '<b>Skill Level</b>: ' + model.database.SKILL_LEVELS_DICT[self.video.skill_level].replace('<', '&lt;').replace('>', '&gt;'),
                          '<b>Global Rating Score</b>: {}/30 ({:.2f}%)'.format(self.video.grs_total, int(self.video.grs_total) / 0.30 ),
                          '    <b>Respect for tissue</b>: ' + self.getGrs(self.video.grs_tissue, model.database.GRS_TISSUE),
                          '    <b>Suture/needle handling</b>: ' + self.getGrs(self.video.grs_suture, model.database.GRS_SUTURE),
                          '    <b>Time and motion</b>: ' + self.getGrs(self.video.grs_time, model.database.GRS_TIME),
                          '    <b>Flow of operation</b>: ' + self.getGrs(self.video.grs_flow, model.database.GRS_FLOW),
                          '    <b>Overall performance</b>: ' + self.getGrs(self.video.grs_performance, None),
                          '    <b>Quality of final product</b>: ' + self.getGrs(self.video.grs_quality, None),
                      ]))


def start(config) :
    GObject.threads_init()
    Gst.init(None)

    model.database.connectFileDb(config)

    handler = Handler("gui.glade", config[DIR_CONFIG])
    return Gtk.main()