import re
import model
import model.database
import model.kinematics
from gi.repository import GObject, Gst, Gtk
import os
import peewee
from peewee import fn
from videoplayer import VideoPlayer
import livediagram
import matplotlib
#from matplotlibdrawingarea import TimeLinearPlot, TrajectoryPlot
from matplotlibdrawingarea import TrajectoryPlot
from collections import namedtuple
from accordion import Accordion

def debug(vars) :
    try :
        from IPython import embed
        for x in vars :
            locals()[x] = vars[x]
        embed()
    except :
        pass

GestureStoreItem = namedtuple('GestureStoreItem', 'id desc start end')

DIR_CONFIG = 'dir_config'
READY = "Ready"

framesToMinutesStr = lambda s : "{:02d}:{:02d}".format(s // 1800, (s // 30) % 60)

GESTURE_ID, GESTURE_NAME, GESTURE_START, GESTURE_END = range(4)

EXPORT_TARGET_EVERYTHING = 'everything'
EXPORT_TARGET_TASK = 'task'
EXPORT_TARGET_VIDEO = 'video'
EXPORT_TARGET_GESTURES = 'gestures'
EXPORT_TARGET_GESTURE_TYPES = 'gesture_types'

EXPORT_SQL_JOINS_WITHGESTURES = 'inner join Transcript on Kinematic.video_id = Transcript.video_id and Kinematic.frame between Transcript.start and Transcript.end'


def add_filter_to_chooser(dialog, name, pattern) :
    """
    Adds a new pattern-based file filter to  the FileChooserDialog
    :param dialog: The Gtk.FileChooserDialog.
    :param name: The display name of the filter.
    :param pattern: The text pattern to use. (eg.: "*.csv")
    :return: None
    """
    file_filter_type = Gtk.FileFilter()
    file_filter_type.add_pattern(pattern)
    file_filter_type.set_name(name)
    dialog.add_filter(file_filter_type)


class Handler (VideoPlayer):
    __task_name = ""
    __video_name = ""
    __video_length = 0
    __video_search = ""
    __app_status = ""
    __export_filename_filter = False
    __export_filename_filter_regex = False

    video = None
    selected = ['mtm_left_pos_x', 'mtm_left_pos_y', 'mtm_left_pos_z']

    def __init__(self, glade_file, css_file, dir_config):
        VideoPlayer.__init__(self)

        # store init parameters
        self.glade_file = glade_file
        self.css_file = css_file
        self.dir_config = dir_config

        # set up Glade builder
        builder = Gtk.Builder()
        builder.add_from_file(glade_file)
        builder.connect_signals(self)
        self.builder = builder

        # get elements by ID
        self.video_store = builder.get_object("video_store")
        self.kinematic_store = builder.get_object("kinematic_store")
        self.gesture_store = builder.get_object("gesture_store")
        self.main_window = builder.get_object("main_window")
        self.scale_video_position = builder.get_object("scale_video_position")
        self.video_player = builder.get_object("video_player")
        self.label_subject = builder.get_object("label_subject")
        self.gesture_diagram_box = builder.get_object("gesture_diagram_box")
        self.gesture_playlist_selection = builder.get_object("gesture_playlist_selection")
        self.export_dialog = builder.get_object("export_dialog")
        self.export_query = builder.get_object("export_query")
        self.export_filetype_default = builder.get_object("export_filetype_default")

        self.ksp_checkbuttons = builder.get_object("ksp_box").get_children()

        # gui styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(css_file)
        style_context = self.main_window.get_style_context()
        screen = self.main_window.get_screen()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # gui binding
        self.register("video_name", self.main_window, set_converter=lambda x: '{} - staej'.format(x) if x else 'staej')
        self.register_widget("task_name", "label_task_name")
        self.register_widget("video_name", "label_video_name")
        self.register_widget("video_length", "label_video_length", set_converter=framesToMinutesStr)
        self.register_widget("video_position", "scale_video_position")
        self.register_widget("video_search", "entry_video_search")

        playpause_image = builder.get_object("button_playpause").get_child()
        self.register("video_playing", lambda value: playpause_image.set_from_icon_name(
            'media-playback-pause' if value else 'media-playback-start', Gtk.IconSize.BUTTON))

        self.register("app_status", builder.get_object("status").get_children()[0].get_child().get_children()[0])
        self.app_status = READY

        getGestureConverter = lambda n, f = str, d = '' : lambda value :\
            ([f(x[n] if n else i) for i, x in enumerate(self.gesture_spans) if
            x[GESTURE_START] <= value // Gst.FRAME <= x[GESTURE_END]] or [d])[0]
        self.getGestureIndex = getGestureConverter(None, int, 0)

        self.register_widget("video_position", "current_gesture_name", set_converter=getGestureConverter(GESTURE_NAME))
        self.register_widget("video_position", "current_gesture_start",
                             set_converter=getGestureConverter(GESTURE_START, framesToMinutesStr))
        self.register_widget("video_position", "current_gesture_end",
                             set_converter=getGestureConverter(GESTURE_END, framesToMinutesStr))
        self.register("video_position", self.updateTime)

        self.register_widget("export_filename_filter")
        self.register_widget("export_filename_filter_regex")

        # gui additional
        self.live_diagram = livediagram.LiveDiagram(builder.get_object("live_diagram"))
        self.gesture_plot = TrajectoryPlot().pack_into(self.gesture_diagram_box)
        self.main_window.show_all()


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

        # which kinematics trajectory to display (MTM or PSM; MTM is default)
        self.arm_type = 'mtm'

        # finalization
        self.main_window.show_all()
        self.main_window.maximize()
        self.main_window.set_title('staej')
        self.onKspToggled(checkbox_only=True)

        # init export dialog
        self.export_dialog.set_transient_for(self.main_window)
        self.export_dialog.set_modal(self.main_window)
        #self.export_dialog.run()
        #self.export_dialog.hide()
        self.export_accordion = Accordion(self.builder.get_object('export_builder_accordion'), True)

    def register_widget(self, name, widget_id = None, default_value = None, set_converter = None, get_converter = None):
        return self.register(name, self.builder.get_object(widget_id or name),
                             default_value, set_converter, get_converter)

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

    @GObject.Property
    def export_filename_filter(self): return self.__export_filename_filter

    @export_filename_filter.setter
    def export_filename_filter_regex(self, value):
        self.__export_filename_filter = value
        print(value)

    @GObject.Property
    def export_filename_filter_regex(self): return self.__export_filename_filter_regex

    @export_filename_filter_regex.setter
    def export_filename_filter_regex(self, value):
        self.__export_filename_filter_regex = value
        print(value)

    def onExit(self, *args):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit(*args)

    def onVideoSelectionChanged(self, tree_selection):
        store, iter = tree_selection.get_selected()
        if not store or not iter : return
        name, id, selectable = store[iter]
        if not selectable : return

        self.app_status = "Loading..."
        self.video = model.database.Video.get(id = id)
        self.updateVideo()
        self.app_status = READY

    suppress_on_gesture_selection_changed = False
    def onGestureSelectionChanged(self, tree_selection):
        if self.suppress_on_gesture_selection_changed : return
        #print('onGestureSelectionChanged')
        store, iter = tree_selection.get_selected()
        if not store or not iter : return

        id, desc, start, end = store[iter]
        if not (start <= self.video_position / Gst.FRAME <= end) :
            self.video_position = start * Gst.FRAME

    def onKspToggled(self, *dontcare, checkbox_only=False):
        selected_checkboxes = [ x for x in self.ksp_checkbuttons if x.get_active() ]
        self.selected = map(lambda x: x.get_id()[4:], selected_checkboxes)
        if not checkbox_only: self.updateDiagramData()

        for x in self.ksp_checkbuttons: x.get_child().set_text(x.get_id()[4:])
        for checkbox, color in zip(selected_checkboxes, livediagram.getColors(len(selected_checkboxes))):
            label = checkbox.get_child()
            color = "{:02X}{:02X}{:02X}".format(*[int(x * 255) for x in color])
            label.set_markup('<span color="#{}">{}</span>'.format(color, label.get_text()))

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

        colname_i = 0
        for colname in model.kinematics.columns :
            self.kinematics_range[colname] = max(
                -min(getattr(self.kinematics[x],colname) for x in self.kinematics),
                max (getattr(self.kinematics[x],colname) for x in self.kinematics))
            #colname_i += 1
            #print(colname_i)

        self.updateGesturePlot(self.arm_type)

        self.onKspToggled()

    def updateGesturePlot(self, arm_type):
        self.gesture_plot.clear()
        arm_type_label = arm_type.upper()

        self.gesture_plot.addSubplots(
            arm_type_label + ' Left Position',
            [getattr(self.kinematics[x], arm_type + '_left_pos_x') for x in self.kinematics],
            [getattr(self.kinematics[x], arm_type + '_left_pos_y') for x in self.kinematics],
            [getattr(self.kinematics[x], arm_type + '_left_pos_z') for x in self.kinematics],
            arm_type_label +' Right Position',
            [getattr(self.kinematics[x], arm_type + '_right_pos_x') for x in self.kinematics],
            [getattr(self.kinematics[x], arm_type + '_right_pos_y') for x in self.kinematics],
            [getattr(self.kinematics[x], arm_type + '_right_pos_z') for x in self.kinematics],
        )

    def updateDiagramData(self):
        self.live_diagram.data = [[getattr(self.kinematics[x], attr) for x in self.kinematics] for attr in self.selected]

    def updateTime(self, time):
        frame = time // Gst.FRAME
        if frame not in self.kinematics : return

        x = self.kinematic_store.get_iter_first()

        for colname in model.kinematics.columns :
            value = getattr(self.kinematics[frame], colname)
            abs_max = self.kinematics_range[colname]

            self.kinematic_store.set_value(x, 1, value * 50 / abs_max + 50)
            x = self.kinematic_store.iter_next(x)

        self.live_diagram.vline = time / self.video_duration
        self.gesture_plot.highlight_point = frame - 1 # index of the current frame's item in the series

        gesture_index = self.getGestureIndex(time)
        self.gesture_plot.highlight_section = (
            self.gesture_spans[gesture_index][GESTURE_START],
            self.gesture_spans[gesture_index][GESTURE_END])
        self.suppress_on_gesture_selection_changed = True
        self.gesture_playlist_selection.select_iter(self.gesture_store.iter_nth_child(None, gesture_index))
        self.suppress_on_gesture_selection_changed = False

    def getSelectedGesture(self):
        store, iter = self.gesture_playlist_selection.get_selected()
        if store and iter:
            return GestureStoreItem(*store[iter])

    def onExportClicked(self, *dontcare):
        self.export_magnitude = EXPORT_TARGET_EVERYTHING
        self.builder.get_object('export_magnitude_everything').set_active(True)
        self.export_accordion.set(self.export_accordion.first, True)
        self.export_dialog.show()

    def onExportDialogCancel(self, *dontcare):
        'Clean out the SQL entry, reset the checkboxes and hide the dialog.'

        self.builder.get_object('export_magnitude_everything').set_active(True)
        self.export_query.get_buffer().clear()
        for colname in model.kinematics.meta + model.kinematics.columns + model.kinematics.gesture_checkbox_names :
            self.builder.get_object('export_' + colname).set_active(False)

        self.export_filename_filter = ''
        self.export_filename_filter_regex = False

        self.export_dialog.hide()
        return True

    def onExportDialogSave(self, *dontcare):
        # get SQL query
        joins = []
        conditions = []

        if self.export_query.get_text().strip() :
            # get user query
            query = 'SELECT ' + re.sub(r'^\s*SELECT\s*', '', self.export_query.get_text(), flags=re.IGNORECASE)
        else :
            # build query
            checkbuttons = map(lambda x: self.builder.get_object('export_' + x), model.kinematics.meta + model.kinematics.columns + ['gesture_id', 'gesture_description'])
            active = [x.get_name() for x in checkbuttons if x.get_active()]
            selected_columns = ', '.join(active) or '*'

            # join in gestures if needed
            if any(x for x in active if x.startswith('Gesture.')) :
                joins.append(EXPORT_SQL_JOINS_WITHGESTURES)
                joins.append('inner join Gesture on Transcript.gesture_id = Gesture.id')

            if self.export_filename_filter :
                joins.append('inner join Video on Kinematic.video_id = Video.id')
                if self.export_filename_filter_regex :
                    conditions.append("Video.file_name regexp '{}'".format(self.export_filename_filter))
                else :
                    filter_parts = self.export_filename_filter.split(',')
                    fragments = ("Video.file_name like '%{}%'".format(x.strip()) for x in filter_parts)
                    conditions.append('(' + ' or '.join(fragments) + ')')

            if self.export_magnitude == EXPORT_TARGET_EVERYTHING :
                pass
            elif self.export_magnitude == EXPORT_TARGET_TASK :
                if not self.video : return
                videos = model.database.Video.select().where(model.database.Video.task_id == self.video.task_id)
                video_ids = ', '.join(map(str, videos.select(model.database.Video.id)))
                conditions.append('Kinematic.video_id in ({})'.format(video_ids))
            elif self.export_magnitude == EXPORT_TARGET_VIDEO :
                if not self.video : return
                conditions.append('Kinematic.video_id = {}'.format(self.video.id))
            elif self.export_magnitude == EXPORT_TARGET_GESTURES :
                gesture = self.getSelectedGesture()
                if not gesture: return
                conditions.append('Kinematic.video_id = {} and Kinematic.frame between {} and {}'.format(self.video.id, gesture.start, gesture.end))
            elif self.export_magnitude == EXPORT_TARGET_GESTURE_TYPES:
                gesture = self.getSelectedGesture()
                if not gesture: return
                joins.append(EXPORT_SQL_JOINS_WITHGESTURES)
                conditions.append('Transcript.gesture_id = {}'.format(gesture.id))

            joins = ' '.join(set(joins))
            conditions = ' '.join(set(conditions))
            conditions = ('where {}'.format(conditions)) if conditions else ''
            query = 'SELECT {} from Kinematic {} {}'.format(selected_columns.replace('Gesture.id', 'Gesture.id as gesture_id'), joins, conditions)

        # get export file type
        filetype = next(x.get_name().replace('export_filetype_', '') for x in self.export_filetype_default.get_group() if x.get_active())

        # select target file name
        print(query)
        dialog = Gtk.FileChooserDialog('Save Export',
                                       self.main_window,
                                       Gtk.FileChooserAction.SAVE,
                                       ('Cancel', Gtk.ResponseType.CANCEL, 'Save', Gtk.ResponseType.ACCEPT))
        add_filter_to_chooser(dialog, filetype.upper(), '*.' + filetype)
        add_filter_to_chooser(dialog, 'Anything', '*')
        result = dialog.run()
        if result != Gtk.ResponseType.ACCEPT :
            dialog.destroy()
            return
        else :
            filename = dialog.get_filename()
            dialog.destroy()
            if '.' not in filename :
                filename = '{}.{}'.format(filename, filetype)

        # evaluate query
        q = peewee.RawQuery(query)
        q.bind(db)
        results = q.execute()
        arr = list()
        for row in list(results):
            r = list()
            for name in results.columns:
                r.append(row[name])
            arr.append(r)

        if filetype == 'mat' :
            # export MAT file
            import scipy.io
            scipy.io.savemat(filename, { 'result' : arr })
        elif filetype == 'csv' :
            import csv
            arr.insert(0, results.columns)
            with open(filename, 'w') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(arr)

        #close dialog
        self.onExportDialogCancel()

    def onExportMagnitudeChanged(self, radio):
        if radio.get_active() :
            self.export_magnitude = radio.get_name()

    def onGestureDiagramTargetChanged(self, radio):
        if radio.get_active() :
            self.arm_type = radio.get_name().rpartition('_')[-1]
            self.updateGesturePlot(self.arm_type)


Gtk.TextBuffer.get_all_text = lambda buffer: buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
Gtk.TextBuffer.clear = lambda buffer: buffer.delete(buffer.get_start_iter(), buffer.get_end_iter())

Gtk.TextView.get_text = lambda textview: textview.get_buffer().get_all_text()
Gtk.TextView.set_text = lambda textview, text: textview.get_buffer().set_text(text, -1)


def start(config) :
    font = {'family': 'DejaVu Sans',
            'weight': 'normal',
            'size': 8}

    matplotlib.rc('font', **font)

    GObject.threads_init()
    Gst.init(None)

    global db
    db = model.database.connectFileDb(config)

    Handler("gui.glade", "gui.css", config[DIR_CONFIG])
    return Gtk.main()
