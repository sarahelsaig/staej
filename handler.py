import model
import model.database
from gi.repository import GObject, Gst, Gtk
import os
from peewee import fn
from videoplayer import VideoPlayer
from livediagram import LiveDiagram
from IPython import embed


DIR_CONFIG = 'dir_config'
READY = "Ready"

framesToMinutesStr = lambda s : "{:02d}:{:02d}".format(s // 1800, (s // 30) % 60)

GESTURE_ID, GESTURE_NAME, GESTURE_START, GESTURE_END = range(4)
class Handler (VideoPlayer):
    __task_name = ""
    __video_name = ""
    __video_length = 0
    __video_search = ""
    __app_status = ""

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
                      set_converter=framesToMinutesStr)
        self.register("video_position", self.scale_video_position)
        self.register("video_search", builder.get_object("entry_video_search"))

        playpause_image = builder.get_object("button_playpause").get_child()
        self.register("video_playing", lambda value: playpause_image.set_from_icon_name(
            'media-playback-pause' if value else 'media-playback-start', Gtk.IconSize.BUTTON))

        self.register("app_status", builder.get_object("status").get_children()[0].get_child().get_children()[0])
        self.app_status = READY

        getGestureConverter = lambda n, f = str : lambda value :\
            ([f(x[n]) for x in self.gesture_spans if x[GESTURE_START] <= value // Gst.FRAME <= x[GESTURE_END]] or [''])[0]
        self.register("video_position", builder.get_object("current_gesture_name"),
                      set_converter=getGestureConverter(GESTURE_NAME))
        self.register("video_position", builder.get_object("current_gesture_start"),
                      set_converter=getGestureConverter(GESTURE_START, framesToMinutesStr))
        self.register("video_position", builder.get_object("current_gesture_end"),
                      set_converter=getGestureConverter(GESTURE_END, framesToMinutesStr))
        self.register("video_position", builder.get_object("current_gesture_end"),
                      set_converter=getGestureConverter(GESTURE_END, framesToMinutesStr))
        self.register("video_position", self.updateKinematicStore)

        self.live_diagram = LiveDiagram(builder.get_object("live_diagram"))

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
        self.gesture_spans = list()

        # kinematics
        self.kinematics = dict()

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

    @GObject.Property(type=str)
    def app_status(self): return self.__app_status

    @app_status.setter
    def app_status(self, value):
        self.__app_status = str(value)

    def onExit(self, *args):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit(*args)

    def onVideoSelectionChanged(self, tree_selection):
        store, item = tree_selection.get_selected()
        if not store or not item : return
        name, id, selectable = store[item]
        if not selectable : return

        self.app_status = "Loading..."
        self.video = model.database.Video.get(id = id)
        self.updateVideo()
        self.app_status = READY

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

        #print (model[iter][0].lower(), query, query in model[iter][0].lower())
        if query in model[iter][0].lower() :
            return True
        child = model.iter_children(iter)
        while child is not None :
            if self.videoStoreFilter(model, child, user_data) :
                return True
            child = model.iter_next(child)
        return False


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
            self.video_name + '_capture2.avi')
        self.load(file_name)

        # update the Gestures tab
        self.gesture_store.clear()
        self.gesture_spans = list()
        for x in model.database.Transcript.select().where(model.database.Transcript.video_id == self.video.id).order_by(model.database.Transcript.start) :
            gesture_store_item = [x.gesture_id, self.gestures[x.gesture_id], x.start, x.end]
            self.gesture_store.append(gesture_store_item)
            self.gesture_spans.append(gesture_store_item)

        # update subject info
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

        # download kinematics
        self.kinematics = dict()
        self.kinematics_range = dict()
        for x in model.database.Kinematic.select().where(model.database.Kinematic.video_id == self.video.id).order_by(model.database.Kinematic.frame) :
            self.kinematics[x.frame] = x
        self.kinematics_range['mtm_left_pos_x'] = max(
            -min(self.kinematics[x].mtm_left_pos_x for x in self.kinematics),
            max(self.kinematics[x].mtm_left_pos_x for x in self.kinematics))
        print(1)
        self.kinematics_range['mtm_left_pos_y'] = max(
            -min(self.kinematics[x].mtm_left_pos_y for x in self.kinematics),
            max(self.kinematics[x].mtm_left_pos_y for x in self.kinematics))
        print(1)
        self.kinematics_range['mtm_left_pos_z'] = max(
            -min(self.kinematics[x].mtm_left_pos_z for x in self.kinematics),
            max(self.kinematics[x].mtm_left_pos_z for x in self.kinematics))
        print(1)
        self.kinematics_range['mtm_left_rot_11'] = max(
            -min(self.kinematics[x].mtm_left_rot_11 for x in self.kinematics),
            max(self.kinematics[x].mtm_left_rot_11 for x in self.kinematics))
        print(1)
        self.kinematics_range['mtm_left_rot_12'] = max(
            -min(self.kinematics[x].mtm_left_rot_12 for x in self.kinematics),
            max(self.kinematics[x].mtm_left_rot_12 for x in self.kinematics))
        print(1)
        self.kinematics_range['mtm_left_rot_13'] = max(
            -min(self.kinematics[x].mtm_left_rot_13 for x in self.kinematics),
            max(self.kinematics[x].mtm_left_rot_13 for x in self.kinematics))
        print(1)
        self.kinematics_range['mtm_left_rot_21'] = max(
            -min(self.kinematics[x].mtm_left_rot_21 for x in self.kinematics),
            max(self.kinematics[x].mtm_left_rot_21 for x in self.kinematics))
        print(1)
        self.kinematics_range['mtm_left_rot_22'] = max(
            -min(self.kinematics[x].mtm_left_rot_22 for x in self.kinematics),
            max(self.kinematics[x].mtm_left_rot_22 for x in self.kinematics))
        self.kinematics_range['mtm_left_rot_23'] = max(
            -min(self.kinematics[x].mtm_left_rot_23 for x in self.kinematics),
            max(self.kinematics[x].mtm_left_rot_23 for x in self.kinematics))
        self.kinematics_range['mtm_left_rot_31'] = max(
            -min(self.kinematics[x].mtm_left_rot_31 for x in self.kinematics),
            max(self.kinematics[x].mtm_left_rot_31 for x in self.kinematics))
        self.kinematics_range['mtm_left_rot_32'] = max(
            -min(self.kinematics[x].mtm_left_rot_32 for x in self.kinematics),
            max(self.kinematics[x].mtm_left_rot_32 for x in self.kinematics))
        self.kinematics_range['mtm_left_rot_33'] = max(
            -min(self.kinematics[x].mtm_left_rot_33 for x in self.kinematics),
            max(self.kinematics[x].mtm_left_rot_33 for x in self.kinematics))
        self.kinematics_range['mtm_left_velocity_a'] = max(
            -min(self.kinematics[x].mtm_left_velocity_a for x in self.kinematics),
            max(self.kinematics[x].mtm_left_velocity_a for x in self.kinematics))
        self.kinematics_range['mtm_left_velocity_b'] = max(
            -min(self.kinematics[x].mtm_left_velocity_b for x in self.kinematics),
            max(self.kinematics[x].mtm_left_velocity_b for x in self.kinematics))
        self.kinematics_range['mtm_left_velocity_c'] = max(
            -min(self.kinematics[x].mtm_left_velocity_c for x in self.kinematics),
            max(self.kinematics[x].mtm_left_velocity_c for x in self.kinematics))
        self.kinematics_range['mtm_left_velocity_x'] = max(
            -min(self.kinematics[x].mtm_left_velocity_x for x in self.kinematics),
            max(self.kinematics[x].mtm_left_velocity_x for x in self.kinematics))
        self.kinematics_range['mtm_left_velocity_y'] = max(
            -min(self.kinematics[x].mtm_left_velocity_y for x in self.kinematics),
            max(self.kinematics[x].mtm_left_velocity_y for x in self.kinematics))
        self.kinematics_range['mtm_left_velocity_z'] = max(
            -min(self.kinematics[x].mtm_left_velocity_z for x in self.kinematics),
            max(self.kinematics[x].mtm_left_velocity_z for x in self.kinematics))
        self.kinematics_range['mtm_left_gripper'] = max(
            -min(self.kinematics[x].mtm_left_gripper for x in self.kinematics),
            max(self.kinematics[x].mtm_left_gripper for x in self.kinematics))
        self.kinematics_range['mtm_right_pos_x'] = max(
            -min(self.kinematics[x].mtm_right_pos_x for x in self.kinematics),
            max(self.kinematics[x].mtm_right_pos_x for x in self.kinematics))
        self.kinematics_range['mtm_right_pos_y'] = max(
            -min(self.kinematics[x].mtm_right_pos_y for x in self.kinematics),
            max(self.kinematics[x].mtm_right_pos_y for x in self.kinematics))
        self.kinematics_range['mtm_right_pos_z'] = max(
            -min(self.kinematics[x].mtm_right_pos_z for x in self.kinematics),
            max(self.kinematics[x].mtm_right_pos_z for x in self.kinematics))
        self.kinematics_range['mtm_right_rot_11'] = max(
            -min(self.kinematics[x].mtm_right_rot_11 for x in self.kinematics),
            max(self.kinematics[x].mtm_right_rot_11 for x in self.kinematics))
        self.kinematics_range['mtm_right_rot_12'] = max(
            -min(self.kinematics[x].mtm_right_rot_12 for x in self.kinematics),
            max(self.kinematics[x].mtm_right_rot_12 for x in self.kinematics))
        self.kinematics_range['mtm_right_rot_13'] = max(
            -min(self.kinematics[x].mtm_right_rot_13 for x in self.kinematics),
            max(self.kinematics[x].mtm_right_rot_13 for x in self.kinematics))
        self.kinematics_range['mtm_right_rot_21'] = max(
            -min(self.kinematics[x].mtm_right_rot_21 for x in self.kinematics),
            max(self.kinematics[x].mtm_right_rot_21 for x in self.kinematics))
        self.kinematics_range['mtm_right_rot_22'] = max(
            -min(self.kinematics[x].mtm_right_rot_22 for x in self.kinematics),
            max(self.kinematics[x].mtm_right_rot_22 for x in self.kinematics))
        self.kinematics_range['mtm_right_rot_23'] = max(
            -min(self.kinematics[x].mtm_right_rot_23 for x in self.kinematics),
            max(self.kinematics[x].mtm_right_rot_23 for x in self.kinematics))
        self.kinematics_range['mtm_right_rot_31'] = max(
            -min(self.kinematics[x].mtm_right_rot_31 for x in self.kinematics),
            max(self.kinematics[x].mtm_right_rot_31 for x in self.kinematics))
        self.kinematics_range['mtm_right_rot_32'] = max(
            -min(self.kinematics[x].mtm_right_rot_32 for x in self.kinematics),
            max(self.kinematics[x].mtm_right_rot_32 for x in self.kinematics))
        self.kinematics_range['mtm_right_rot_33'] = max(
            -min(self.kinematics[x].mtm_right_rot_33 for x in self.kinematics),
            max(self.kinematics[x].mtm_right_rot_33 for x in self.kinematics))
        self.kinematics_range['mtm_right_velocity_a'] = max(
            -min(self.kinematics[x].mtm_right_velocity_a for x in self.kinematics),
            max(self.kinematics[x].mtm_right_velocity_a for x in self.kinematics))
        self.kinematics_range['mtm_right_velocity_b'] = max(
            -min(self.kinematics[x].mtm_right_velocity_b for x in self.kinematics),
            max(self.kinematics[x].mtm_right_velocity_b for x in self.kinematics))
        self.kinematics_range['mtm_right_velocity_c'] = max(
            -min(self.kinematics[x].mtm_right_velocity_c for x in self.kinematics),
            max(self.kinematics[x].mtm_right_velocity_c for x in self.kinematics))
        self.kinematics_range['mtm_right_velocity_x'] = max(
            -min(self.kinematics[x].mtm_right_velocity_x for x in self.kinematics),
            max(self.kinematics[x].mtm_right_velocity_x for x in self.kinematics))
        self.kinematics_range['mtm_right_velocity_y'] = max(
            -min(self.kinematics[x].mtm_right_velocity_y for x in self.kinematics),
            max(self.kinematics[x].mtm_right_velocity_y for x in self.kinematics))
        self.kinematics_range['mtm_right_velocity_z'] = max(
            -min(self.kinematics[x].mtm_right_velocity_z for x in self.kinematics),
            max(self.kinematics[x].mtm_right_velocity_z for x in self.kinematics))
        self.kinematics_range['mtm_right_gripper'] = max(
            -min(self.kinematics[x].mtm_right_gripper for x in self.kinematics),
            max(self.kinematics[x].mtm_right_gripper for x in self.kinematics))
        self.kinematics_range['psm_left_pos_x'] = max(
            -min(self.kinematics[x].psm_left_pos_x for x in self.kinematics),
            max(self.kinematics[x].psm_left_pos_x for x in self.kinematics))
        self.kinematics_range['psm_left_pos_y'] = max(
            -min(self.kinematics[x].psm_left_pos_y for x in self.kinematics),
            max(self.kinematics[x].psm_left_pos_y for x in self.kinematics))
        self.kinematics_range['psm_left_pos_z'] = max(
            -min(self.kinematics[x].psm_left_pos_z for x in self.kinematics),
            max(self.kinematics[x].psm_left_pos_z for x in self.kinematics))
        self.kinematics_range['psm_left_rot_11'] = max(
            -min(self.kinematics[x].psm_left_rot_11 for x in self.kinematics),
            max(self.kinematics[x].psm_left_rot_11 for x in self.kinematics))
        self.kinematics_range['psm_left_rot_12'] = max(
            -min(self.kinematics[x].psm_left_rot_12 for x in self.kinematics),
            max(self.kinematics[x].psm_left_rot_12 for x in self.kinematics))
        self.kinematics_range['psm_left_rot_13'] = max(
            -min(self.kinematics[x].psm_left_rot_13 for x in self.kinematics),
            max(self.kinematics[x].psm_left_rot_13 for x in self.kinematics))
        self.kinematics_range['psm_left_rot_21'] = max(
            -min(self.kinematics[x].psm_left_rot_21 for x in self.kinematics),
            max(self.kinematics[x].psm_left_rot_21 for x in self.kinematics))
        self.kinematics_range['psm_left_rot_22'] = max(
            -min(self.kinematics[x].psm_left_rot_22 for x in self.kinematics),
            max(self.kinematics[x].psm_left_rot_22 for x in self.kinematics))
        self.kinematics_range['psm_left_rot_23'] = max(
            -min(self.kinematics[x].psm_left_rot_23 for x in self.kinematics),
            max(self.kinematics[x].psm_left_rot_23 for x in self.kinematics))
        self.kinematics_range['psm_left_rot_31'] = max(
            -min(self.kinematics[x].psm_left_rot_31 for x in self.kinematics),
            max(self.kinematics[x].psm_left_rot_31 for x in self.kinematics))
        self.kinematics_range['psm_left_rot_32'] = max(
            -min(self.kinematics[x].psm_left_rot_32 for x in self.kinematics),
            max(self.kinematics[x].psm_left_rot_32 for x in self.kinematics))
        self.kinematics_range['psm_left_rot_33'] = max(
            -min(self.kinematics[x].psm_left_rot_33 for x in self.kinematics),
            max(self.kinematics[x].psm_left_rot_33 for x in self.kinematics))
        self.kinematics_range['psm_left_velocity_a'] = max(
            -min(self.kinematics[x].psm_left_velocity_a for x in self.kinematics),
            max(self.kinematics[x].psm_left_velocity_a for x in self.kinematics))
        self.kinematics_range['psm_left_velocity_b'] = max(
            -min(self.kinematics[x].psm_left_velocity_b for x in self.kinematics),
            max(self.kinematics[x].psm_left_velocity_b for x in self.kinematics))
        self.kinematics_range['psm_left_velocity_c'] = max(
            -min(self.kinematics[x].psm_left_velocity_c for x in self.kinematics),
            max(self.kinematics[x].psm_left_velocity_c for x in self.kinematics))
        self.kinematics_range['psm_left_velocity_x'] = max(
            -min(self.kinematics[x].psm_left_velocity_x for x in self.kinematics),
            max(self.kinematics[x].psm_left_velocity_x for x in self.kinematics))
        self.kinematics_range['psm_left_velocity_y'] = max(
            -min(self.kinematics[x].psm_left_velocity_y for x in self.kinematics),
            max(self.kinematics[x].psm_left_velocity_y for x in self.kinematics))
        self.kinematics_range['psm_left_velocity_z'] = max(
            -min(self.kinematics[x].psm_left_velocity_z for x in self.kinematics),
            max(self.kinematics[x].psm_left_velocity_z for x in self.kinematics))
        self.kinematics_range['psm_left_gripper'] = max(
            -min(self.kinematics[x].psm_left_gripper for x in self.kinematics),
            max(self.kinematics[x].psm_left_gripper for x in self.kinematics))
        self.kinematics_range['psm_right_pos_x'] = max(
            -min(self.kinematics[x].psm_right_pos_x for x in self.kinematics),
            max(self.kinematics[x].psm_right_pos_x for x in self.kinematics))
        self.kinematics_range['psm_right_pos_y'] = max(
            -min(self.kinematics[x].psm_right_pos_y for x in self.kinematics),
            max(self.kinematics[x].psm_right_pos_y for x in self.kinematics))
        self.kinematics_range['psm_right_pos_z'] = max(
            -min(self.kinematics[x].psm_right_pos_z for x in self.kinematics),
            max(self.kinematics[x].psm_right_pos_z for x in self.kinematics))
        self.kinematics_range['psm_right_rot_11'] = max(
            -min(self.kinematics[x].psm_right_rot_11 for x in self.kinematics),
            max(self.kinematics[x].psm_right_rot_11 for x in self.kinematics))
        self.kinematics_range['psm_right_rot_12'] = max(
            -min(self.kinematics[x].psm_right_rot_12 for x in self.kinematics),
            max(self.kinematics[x].psm_right_rot_12 for x in self.kinematics))
        self.kinematics_range['psm_right_rot_13'] = max(
            -min(self.kinematics[x].psm_right_rot_13 for x in self.kinematics),
            max(self.kinematics[x].psm_right_rot_13 for x in self.kinematics))
        self.kinematics_range['psm_right_rot_21'] = max(
            -min(self.kinematics[x].psm_right_rot_21 for x in self.kinematics),
            max(self.kinematics[x].psm_right_rot_21 for x in self.kinematics))
        self.kinematics_range['psm_right_rot_22'] = max(
            -min(self.kinematics[x].psm_right_rot_22 for x in self.kinematics),
            max(self.kinematics[x].psm_right_rot_22 for x in self.kinematics))
        self.kinematics_range['psm_right_rot_23'] = max(
            -min(self.kinematics[x].psm_right_rot_23 for x in self.kinematics),
            max(self.kinematics[x].psm_right_rot_23 for x in self.kinematics))
        self.kinematics_range['psm_right_rot_31'] = max(
            -min(self.kinematics[x].psm_right_rot_31 for x in self.kinematics),
            max(self.kinematics[x].psm_right_rot_31 for x in self.kinematics))
        self.kinematics_range['psm_right_rot_32'] = max(
            -min(self.kinematics[x].psm_right_rot_32 for x in self.kinematics),
            max(self.kinematics[x].psm_right_rot_32 for x in self.kinematics))
        self.kinematics_range['psm_right_rot_33'] = max(
            -min(self.kinematics[x].psm_right_rot_33 for x in self.kinematics),
            max(self.kinematics[x].psm_right_rot_33 for x in self.kinematics))
        self.kinematics_range['psm_right_velocity_a'] = max(
            -min(self.kinematics[x].psm_right_velocity_a for x in self.kinematics),
            max(self.kinematics[x].psm_right_velocity_a for x in self.kinematics))
        self.kinematics_range['psm_right_velocity_b'] = max(
            -min(self.kinematics[x].psm_right_velocity_b for x in self.kinematics),
            max(self.kinematics[x].psm_right_velocity_b for x in self.kinematics))
        self.kinematics_range['psm_right_velocity_c'] = max(
            -min(self.kinematics[x].psm_right_velocity_c for x in self.kinematics),
            max(self.kinematics[x].psm_right_velocity_c for x in self.kinematics))
        self.kinematics_range['psm_right_velocity_x'] = max(
            -min(self.kinematics[x].psm_right_velocity_x for x in self.kinematics),
            max(self.kinematics[x].psm_right_velocity_x for x in self.kinematics))
        self.kinematics_range['psm_right_velocity_y'] = max(
            -min(self.kinematics[x].psm_right_velocity_y for x in self.kinematics),
            max(self.kinematics[x].psm_right_velocity_y for x in self.kinematics))
        self.kinematics_range['psm_right_velocity_z'] = max(
            -min(self.kinematics[x].psm_right_velocity_z for x in self.kinematics),
            max(self.kinematics[x].psm_right_velocity_z for x in self.kinematics))
        self.kinematics_range['psm_right_gripper'] = max(
            -min(self.kinematics[x].psm_right_gripper for x in self.kinematics),
            max(self.kinematics[x].psm_right_gripper for x in self.kinematics))

        selected = ['mtm_left_pos_x', 'mtm_left_pos_y', 'mtm_left_pos_z']
        self.live_diagram.data = [[getattr(self.kinematics[x], attr) for x in self.kinematics] for attr in selected]
        print (self.live_diagram.data)

    def updateKinematicStore(self, time):
        frame = time // Gst.FRAME
        if frame not in self.kinematics : return

        k = self.kinematics[frame]
        x = self.kinematic_store.get_iter_first()

        normalize = lambda value, abs_max : value * 50 / abs_max + 50
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_pos_x, self.kinematics_range['mtm_left_pos_x'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_pos_y, self.kinematics_range['mtm_left_pos_y'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_pos_z, self.kinematics_range['mtm_left_pos_z'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_rot_11, self.kinematics_range['mtm_left_rot_11'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_rot_12, self.kinematics_range['mtm_left_rot_12'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_rot_13, self.kinematics_range['mtm_left_rot_13'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_rot_21, self.kinematics_range['mtm_left_rot_21'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_rot_22, self.kinematics_range['mtm_left_rot_22'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_rot_23, self.kinematics_range['mtm_left_rot_23'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_rot_31, self.kinematics_range['mtm_left_rot_31'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_rot_32, self.kinematics_range['mtm_left_rot_32'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_rot_33, self.kinematics_range['mtm_left_rot_33'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_velocity_a, self.kinematics_range['mtm_left_velocity_a'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_velocity_b, self.kinematics_range['mtm_left_velocity_b'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_velocity_c, self.kinematics_range['mtm_left_velocity_c'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_velocity_x, self.kinematics_range['mtm_left_velocity_x'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_velocity_y, self.kinematics_range['mtm_left_velocity_y'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_velocity_z, self.kinematics_range['mtm_left_velocity_z'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_left_gripper, self.kinematics_range['mtm_left_gripper'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_pos_x, self.kinematics_range['mtm_right_pos_x'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_pos_y, self.kinematics_range['mtm_right_pos_y'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_pos_z, self.kinematics_range['mtm_right_pos_z'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_rot_11, self.kinematics_range['mtm_right_rot_11'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_rot_12, self.kinematics_range['mtm_right_rot_12'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_rot_13, self.kinematics_range['mtm_right_rot_13'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_rot_21, self.kinematics_range['mtm_right_rot_21'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_rot_22, self.kinematics_range['mtm_right_rot_22'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_rot_23, self.kinematics_range['mtm_right_rot_23'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_rot_31, self.kinematics_range['mtm_right_rot_31'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_rot_32, self.kinematics_range['mtm_right_rot_32'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_rot_33, self.kinematics_range['mtm_right_rot_33'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_velocity_a, self.kinematics_range['mtm_right_velocity_a'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_velocity_b, self.kinematics_range['mtm_right_velocity_b'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_velocity_c, self.kinematics_range['mtm_right_velocity_c'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_velocity_x, self.kinematics_range['mtm_right_velocity_x'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_velocity_y, self.kinematics_range['mtm_right_velocity_y'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_velocity_z, self.kinematics_range['mtm_right_velocity_z'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.mtm_right_gripper, self.kinematics_range['mtm_right_gripper'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_pos_x, self.kinematics_range['psm_left_pos_x'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_pos_y, self.kinematics_range['psm_left_pos_y'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_pos_z, self.kinematics_range['psm_left_pos_z'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_rot_11, self.kinematics_range['psm_left_rot_11'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_rot_12, self.kinematics_range['psm_left_rot_12'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_rot_13, self.kinematics_range['psm_left_rot_13'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_rot_21, self.kinematics_range['psm_left_rot_21'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_rot_22, self.kinematics_range['psm_left_rot_22'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_rot_23, self.kinematics_range['psm_left_rot_23'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_rot_31, self.kinematics_range['psm_left_rot_31'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_rot_32, self.kinematics_range['psm_left_rot_32'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_rot_33, self.kinematics_range['psm_left_rot_33'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_velocity_a, self.kinematics_range['psm_left_velocity_a'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_velocity_b, self.kinematics_range['psm_left_velocity_b'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_velocity_c, self.kinematics_range['psm_left_velocity_c'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_velocity_x, self.kinematics_range['psm_left_velocity_x'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_velocity_y, self.kinematics_range['psm_left_velocity_y'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_velocity_z, self.kinematics_range['psm_left_velocity_z'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_left_gripper, self.kinematics_range['psm_left_gripper'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_pos_x, self.kinematics_range['psm_right_pos_x'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_pos_y, self.kinematics_range['psm_right_pos_y'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_pos_z, self.kinematics_range['psm_right_pos_z'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_rot_11, self.kinematics_range['psm_right_rot_11'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_rot_12, self.kinematics_range['psm_right_rot_12'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_rot_13, self.kinematics_range['psm_right_rot_13'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_rot_21, self.kinematics_range['psm_right_rot_21'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_rot_22, self.kinematics_range['psm_right_rot_22'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_rot_23, self.kinematics_range['psm_right_rot_23'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_rot_31, self.kinematics_range['psm_right_rot_31'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_rot_32, self.kinematics_range['psm_right_rot_32'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_rot_33, self.kinematics_range['psm_right_rot_33'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_velocity_a, self.kinematics_range['psm_right_velocity_a'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_velocity_b, self.kinematics_range['psm_right_velocity_b'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_velocity_c, self.kinematics_range['psm_right_velocity_c'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_velocity_x, self.kinematics_range['psm_right_velocity_x'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_velocity_y, self.kinematics_range['psm_right_velocity_y'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_velocity_z, self.kinematics_range['psm_right_velocity_z'])); x = self.kinematic_store.iter_next(x)
        self.kinematic_store.set_value(x, 1, normalize(k.psm_right_gripper, self.kinematics_range['psm_right_gripper'])); x = self.kinematic_store.iter_next(x)


def start(config) :
    GObject.threads_init()
    Gst.init(None)

    model.database.connectFileDb(config)

    handler = Handler("gui.glade", config[DIR_CONFIG])
    return Gtk.main()
