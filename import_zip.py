# depends: peewee,
# optdepends: cython

import zipfile
import csv
import model
import model.database
from os import path, makedirs
from os.path import dirname

EXCEPTION_INCORRECT_NAME = 'Incorrect archive, must have files like `TASK/video/VIDEO_capture.avi`'
EXCEPTION_MISSING_META_FILE = 'Meta file is missing! Expected `meta_file_TASK.txt`.'

DIR_TASKS = 'dir_tasks'
FILE_DB = 'file_db'


def next_or_default(generator, default=None) :
    """Gets the next item from the generator or the value of default if the generator stopped."""
    try :
        return next(generator)
    except StopIteration :
        return default


def read_binary_as_text(binary_file, encoding='utf8'):
    """Reads the contents of a binary file as text with the specified encoding."""
    while True:
        line = binary_file.readline().decode(encoding)
        if not line :
            return
        yield line


def read_lines_as_csv(file_descriptor, delimiter='\t', line_cb=None) :
    ret = csv.reader(read_binary_as_text(file_descriptor), delimiter=delimiter)
    if line_cb is None :
        return ret

    if line_cb :
        def line_cb(coll) : return [x for x in coll if x]
    else :
        def line_cb(coll) : return [x for x in coll if not x]

    return (line_cb(x) for x in ret)


def connect_file_db(config) :
    file_db = config[FILE_DB]
    return model.database.connect(file_db)


def extract_videos(filename, config) :
    dir_tasks = config[DIR_TASKS]

    db = connect_file_db(config)
    db.execute_sql('PRAGMA journal_mode = OFF')

    with db.atomic() as transaction :
        try :
            with zipfile.ZipFile(filename) as zf :
                # get task name and create video folder
                name = dirname(next_or_default((x for x in zf.namelist() if x.endswith('/video/')), default='').rstrip('/'))
                if not name:
                    raise Exception()

                dir_task = path.join(dir_tasks, name)
                makedirs(dir_task, exist_ok=True)
                print(0)

                # extract videos
                videos = (x for x in zf.namelist() if '/video/' in x and ('_capture1.avi' in x or '_capture2.avi' in x))
                zf.extractall(path=dir_tasks, members=videos)
                print(1)

                gestures = dict(('G{}'.format(x.id), x) for x in model.database.Gesture.select())
                task = model.database.Task(name=name)
                task.save()
                print('task_id:', task.id)
                print(2)

                # open meta file
                meta = next_or_default(x for x in zf.namelist() if 'meta_file' in x.lower())
                if not meta :
                    raise Exception(EXCEPTION_MISSING_META_FILE)
                print(3)
                with zf.open(meta) as file_descriptor_meta :
                    print(4)

                    # from IPython import embed
                    # embed()

                    for row_meta in read_lines_as_csv(file_descriptor_meta) :
                        print(5)
                        video = model.database.Video.new(task.id, row_meta)
                        # video.save(force_insert=True)

                        file_kinematics = next(x for x in zf.namelist() if '/kinematics/' in x and video.file_name in x)
                        with zf.open(file_kinematics) as file_descriptor_kinematics :
                            print(6)
                            frame = 0
                            for row_kinematics in read_lines_as_csv(file_descriptor_kinematics,
                                                                    delimiter=' ', line_cb=True) :
                                frame += 1
                                kinematic = model.database.Kinematic.new(video.id, frame, row_kinematics)
                            print(7, video.id , kinematic.id)

                        # db.begin()
                        file_transcript = next(x for x in zf.namelist() if '/transcriptions/' in x and video.file_name in x)
                        with zf.open(file_transcript) as file_descriptor_transcript :
                            print(8)

                            for row_descriptor_transcript in read_lines_as_csv(file_descriptor_transcript, delimiter=' ') :
                                transcript = model.database.Transcript.new(
                                    task.id, video.id, row_descriptor_transcript, gestures)
                            print(9, video.id , transcript.id)

                        # db.commit()
        except Exception as e :
            transaction.rollback()
            raise e

        return name
