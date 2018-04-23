import peewee

SKILL_LEVELS = ('N', 'I', 'E')

FILE_DB = 'file_db'
def connectFileDb(config) :
    file_db = config[FILE_DB]
    return connect(file_db)

def connect(file):
    """
    Loads the SQLite db from the selected file and binds the (Task, Video, Gesture, Transcript, Kinematic) tables to it.
    :param file: The path of the database.
    :return: The database object.
    """
    db = peewee.SqliteDatabase(file)
    db.bind((Task, Video, Gesture, Transcript, Kinematic))
    return db


class Task(peewee.Model):
    """
    This table names the exercise that's performed in a collection of videos.
    """

    id = peewee.PrimaryKeyField()
    name = peewee.TextField()


class Video(peewee.Model):
    """
    This table contains the information about a video and its metadata.
    """

    id = peewee.PrimaryKeyField()
    task_id = peewee.IntegerField()
    file_name = peewee.TextField()
    skill_level = peewee.CharField(max_length=1)
    grs_total = peewee.TextField()
    grs_tissue = peewee.TextField()
    grs_suture = peewee.TextField()
    grs_time = peewee.TextField()
    grs_flow = peewee.TextField()
    grs_performance = peewee.TextField()
    grs_quality = peewee.TextField()

    @staticmethod
    def new(task_id, str_row):
        """
        Creates a new Video item based on the Task ID and the string row from the meta file.
        :param task_id: Database ID of the associated task.
        :param str_row: An indexable string collection of a line (including the empty separator columns).
        :return: A new Video item.
        """
        file_name = '' if len(str_row) == 0 or not str_row[0] else str_row[0]
        skill_level = 0 if len(str_row) <= 2 or not str_row[2] else (SKILL_LEVELS.index(str_row[2]) + 1)
        grs_total = 0 if len(str_row) <= 3 or not str_row[3] else int(str_row[3])
        grs_tissue = 0 if len(str_row) <= 5 or not str_row[5] else int(str_row[5])
        grs_suture = 0 if len(str_row) <= 6 or not str_row[6] else int(str_row[6])
        grs_time = 0 if len(str_row) <= 7 or not str_row[7] else int(str_row[7])
        grs_flow = 0 if len(str_row) <= 8 or not str_row[8] else int(str_row[8])
        grs_performance = 0 if len(str_row) <= 9 or not str_row[9] else int(str_row[9])
        grs_quality = 0 if len(str_row) <= 10 or not str_row[10] else int(str_row[10])
        return Video.create(
            task_id=task_id,
            file_name=file_name,
            skill_level=skill_level,
            grs_total=grs_total,
            grs_tissue=grs_tissue,
            grs_suture=grs_suture,
            grs_time=grs_time,
            grs_flow=grs_flow,
            grs_performance=grs_performance,
            grs_quality=grs_quality)


class Gesture(peewee.Model):
    """
    This table contains the ID and description of a known gesture used in the transcript.
    """

    id = peewee.PrimaryKeyField()
    description = peewee.TextField()

    @staticmethod
    def fetch(code):
        """
        Finds the Gesture item based on the string code of G + id (eg. 'G4').
        :param code: String code used in the JIGSAWS file.
        :return: The Gesture item with that ID.
        """
        if type(code) == str:
            if code[0] != 'G':
                raise AttributeError('Incorrect gesture code, must start with G, eg.: "G11".')
            code = int(code[1:])
        return Gesture.get(Gesture.id == code)


class Transcript(peewee.Model):
    """
    This table contains a frame span and the gesture performed during that time.
    """

    id = peewee.PrimaryKeyField()
    video_id = peewee.IntegerField()
    gesture_id = peewee.IntegerField()
    start = peewee.IntegerField()
    end = peewee.IntegerField()

    @property
    def kinematics(self):
        """
        Gets all kinematics data for the frame span of this entry.
        :return: A list of Kinematic entries starting with the frame of self.start up to self.end.
        """
        return Kinematic.select().where(
            Kinematic.video_id == self.video_id and
            self.start <= Kinematic.frame <= self.end
        )

    @staticmethod
    def new(task_id, video_id, str_row, gestures):  # WARNING str_row here is space separated, NOT tab separated!
        """
        Creates a new Transcript item from transcript file row.
        :param task_id: Database ID of the associated task.
        :param video_id: Database ID of the associated video.
        :param str_row: Indexable collection of strings: [start, end, gesture_string]
        :param gestures: Dictionary that contains the known gestures, key is the code, eg G12
        :return: Created database item.
        """

        start = int(str_row[0])
        end = int(str_row[1])
        gesture = None

        gesture = gestures[str_row[2]]
        return Transcript.create(video_id=video_id, gesture_id=gesture.id, start=start, end=end)


class Kinematic(peewee.Model):
    """
    This table contains all of the diagnostics info on a specific frame of a video.
    """

    id = peewee.PrimaryKeyField()
    video_id = peewee.IntegerField()
    frame = peewee.IntegerField()

    mtm_left_pos_x = peewee.FloatField()
    mtm_left_pos_y = peewee.FloatField()
    mtm_left_pos_z = peewee.FloatField()
    mtm_left_rot_11 = peewee.FloatField()
    mtm_left_rot_12 = peewee.FloatField()
    mtm_left_rot_13 = peewee.FloatField()
    mtm_left_rot_21 = peewee.FloatField()
    mtm_left_rot_22 = peewee.FloatField()
    mtm_left_rot_23 = peewee.FloatField()
    mtm_left_rot_31 = peewee.FloatField()
    mtm_left_rot_32 = peewee.FloatField()
    mtm_left_rot_33 = peewee.FloatField()
    mtm_left_velocity_x = peewee.FloatField()
    mtm_left_velocity_y = peewee.FloatField()
    mtm_left_velocity_z = peewee.FloatField()
    mtm_left_velocity_a = peewee.FloatField()
    mtm_left_velocity_b = peewee.FloatField()
    mtm_left_velocity_c = peewee.FloatField()
    mtm_left_gripper = peewee.FloatField()
    mtm_right_pos_x = peewee.FloatField()
    mtm_right_pos_y = peewee.FloatField()
    mtm_right_pos_z = peewee.FloatField()
    mtm_right_rot_11 = peewee.FloatField()
    mtm_right_rot_12 = peewee.FloatField()
    mtm_right_rot_13 = peewee.FloatField()
    mtm_right_rot_21 = peewee.FloatField()
    mtm_right_rot_22 = peewee.FloatField()
    mtm_right_rot_23 = peewee.FloatField()
    mtm_right_rot_31 = peewee.FloatField()
    mtm_right_rot_32 = peewee.FloatField()
    mtm_right_rot_33 = peewee.FloatField()
    mtm_right_velocity_x = peewee.FloatField()
    mtm_right_velocity_y = peewee.FloatField()
    mtm_right_velocity_z = peewee.FloatField()
    mtm_right_velocity_a = peewee.FloatField()
    mtm_right_velocity_b = peewee.FloatField()
    mtm_right_velocity_c = peewee.FloatField()
    mtm_right_gripper = peewee.FloatField()
    psm_left_pos_x = peewee.FloatField()
    psm_left_pos_y = peewee.FloatField()
    psm_left_pos_z = peewee.FloatField()
    psm_left_rot_11 = peewee.FloatField()
    psm_left_rot_12 = peewee.FloatField()
    psm_left_rot_13 = peewee.FloatField()
    psm_left_rot_21 = peewee.FloatField()
    psm_left_rot_22 = peewee.FloatField()
    psm_left_rot_23 = peewee.FloatField()
    psm_left_rot_31 = peewee.FloatField()
    psm_left_rot_32 = peewee.FloatField()
    psm_left_rot_33 = peewee.FloatField()
    psm_left_velocity_x = peewee.FloatField()
    psm_left_velocity_y = peewee.FloatField()
    psm_left_velocity_z = peewee.FloatField()
    psm_left_velocity_a = peewee.FloatField()
    psm_left_velocity_b = peewee.FloatField()
    psm_left_velocity_c = peewee.FloatField()
    psm_left_gripper = peewee.FloatField()
    psm_right_pos_x = peewee.FloatField()
    psm_right_pos_y = peewee.FloatField()
    psm_right_pos_z = peewee.FloatField()
    psm_right_rot_11 = peewee.FloatField()
    psm_right_rot_12 = peewee.FloatField()
    psm_right_rot_13 = peewee.FloatField()
    psm_right_rot_21 = peewee.FloatField()
    psm_right_rot_22 = peewee.FloatField()
    psm_right_rot_23 = peewee.FloatField()
    psm_right_rot_31 = peewee.FloatField()
    psm_right_rot_32 = peewee.FloatField()
    psm_right_rot_33 = peewee.FloatField()
    psm_right_velocity_x = peewee.FloatField()
    psm_right_velocity_y = peewee.FloatField()
    psm_right_velocity_z = peewee.FloatField()
    psm_right_velocity_a = peewee.FloatField()
    psm_right_velocity_b = peewee.FloatField()
    psm_right_velocity_c = peewee.FloatField()
    psm_right_gripper = peewee.FloatField()

    @property
    def transcript(self):
        """
        Gets the Transcript row for the action being performed during this frame.
        :return: The Transcript instance.
        """
        return Transcript.get(
            Transcript.video_id == self.video_id and
            Transcript.start <= self.frame <= Transcript.end
        )

    @staticmethod
    def new(video_id, frame, str_row):
        """
        Creates a new Kinematic item from the Kinematics file row.
        :param video_id: Database ID of the associated video.
        :param frame: Current time in frames (1/30 sec)
        :param str_row: Indexable collection of strings: [mtm_left_pos_x, mtm_left_pos_y, ...] (see JIGSAWS paper)
        :return: Created database item.
        """
        return Kinematic.create(
            video_id=video_id,
            frame=frame,
            mtm_left_pos_x=float(str_row[0]),
            mtm_left_pos_y=float(str_row[1]),
            mtm_left_pos_z=float(str_row[2]),
            mtm_left_rot_11=float(str_row[3]),
            mtm_left_rot_12=float(str_row[4]),
            mtm_left_rot_13=float(str_row[5]),
            mtm_left_rot_21=float(str_row[6]),
            mtm_left_rot_22=float(str_row[7]),
            mtm_left_rot_23=float(str_row[8]),
            mtm_left_rot_31=float(str_row[9]),
            mtm_left_rot_32=float(str_row[10]),
            mtm_left_rot_33=float(str_row[11]),
            mtm_left_velocity_x=float(str_row[12]),
            mtm_left_velocity_y=float(str_row[13]),
            mtm_left_velocity_z=float(str_row[14]),
            mtm_left_velocity_a=float(str_row[15]),
            mtm_left_velocity_b=float(str_row[16]),
            mtm_left_velocity_c=float(str_row[17]),
            mtm_left_gripper=float(str_row[18]),
            mtm_right_pos_x=float(str_row[19]),
            mtm_right_pos_y=float(str_row[20]),
            mtm_right_pos_z=float(str_row[21]),
            mtm_right_rot_11=float(str_row[22]),
            mtm_right_rot_12=float(str_row[23]),
            mtm_right_rot_13=float(str_row[24]),
            mtm_right_rot_21=float(str_row[25]),
            mtm_right_rot_22=float(str_row[26]),
            mtm_right_rot_23=float(str_row[27]),
            mtm_right_rot_31=float(str_row[28]),
            mtm_right_rot_32=float(str_row[29]),
            mtm_right_rot_33=float(str_row[30]),
            mtm_right_velocity_x=float(str_row[31]),
            mtm_right_velocity_y=float(str_row[32]),
            mtm_right_velocity_z=float(str_row[33]),
            mtm_right_velocity_a=float(str_row[34]),
            mtm_right_velocity_b=float(str_row[35]),
            mtm_right_velocity_c=float(str_row[36]),
            mtm_right_gripper=float(str_row[37]),
            psm_left_pos_x=float(str_row[38]),
            psm_left_pos_y=float(str_row[39]),
            psm_left_pos_z=float(str_row[40]),
            psm_left_rot_11=float(str_row[41]),
            psm_left_rot_12=float(str_row[42]),
            psm_left_rot_13=float(str_row[43]),
            psm_left_rot_21=float(str_row[44]),
            psm_left_rot_22=float(str_row[45]),
            psm_left_rot_23=float(str_row[46]),
            psm_left_rot_31=float(str_row[47]),
            psm_left_rot_32=float(str_row[48]),
            psm_left_rot_33=float(str_row[49]),
            psm_left_velocity_x=float(str_row[50]),
            psm_left_velocity_y=float(str_row[51]),
            psm_left_velocity_z=float(str_row[52]),
            psm_left_velocity_a=float(str_row[53]),
            psm_left_velocity_b=float(str_row[54]),
            psm_left_velocity_c=float(str_row[55]),
            psm_left_gripper=float(str_row[56]),
            psm_right_pos_x=float(str_row[57]),
            psm_right_pos_y=float(str_row[58]),
            psm_right_pos_z=float(str_row[59]),
            psm_right_rot_11=float(str_row[60]),
            psm_right_rot_12=float(str_row[61]),
            psm_right_rot_13=float(str_row[62]),
            psm_right_rot_21=float(str_row[63]),
            psm_right_rot_22=float(str_row[64]),
            psm_right_rot_23=float(str_row[65]),
            psm_right_rot_31=float(str_row[66]),
            psm_right_rot_32=float(str_row[67]),
            psm_right_rot_33=float(str_row[68]),
            psm_right_velocity_x=float(str_row[69]),
            psm_right_velocity_y=float(str_row[70]),
            psm_right_velocity_z=float(str_row[71]),
            psm_right_velocity_a=float(str_row[72]),
            psm_right_velocity_b=float(str_row[73]),
            psm_right_velocity_c=float(str_row[74]),
            psm_right_gripper=float(str_row[75])
        )
