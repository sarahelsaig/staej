# depends: peewee,
# optdepends: cython

import os
import zipfile
import csv
import model
import model.database

EXCEPTION_INCORRECT_NAME = 'Incorrect archive, must have files like `TASK/video/VIDEO_capture.avi`'
EXCEPTION_MISSING_META_FILE = 'Meta file is missing! Expected `meta_file_TASK.txt`.'

DIR_CONFIG = 'dir_config'
DIR_TASKS = 'dir_tasks'
FILE_DB = 'file_db'

def nextOrDefault(generator, default=None) :
    'Gets the next item from the generator or the value of default if the generator stopped.'
    try : return next(generator)
    except StopIteration : return default


def readBinaryAsText(binary_file, encoding = 'utf8'):
    'Reads the contents of a binary file as text with the specified encoding.'
    while True:
        line = binary_file.readline().decode('utf8')
        if not line : return
        yield line

def readLinesAsCsv(file_descriptor, delimiter='\t', line_cb=None) :
    ret = csv.reader(readBinaryAsText(file_descriptor), delimiter=delimiter)
    if line_cb is None :
        return ret

    if line_cb == True :
        line_cb = lambda coll : [ x for x in coll if x ]
    elif line_cb == False :
        line_cb = lambda coll : [ x for x in coll if not x ]
    return ( line_cb(x) for x in ret )

def connectFileDb(config) :
    file_db = config[FILE_DB]
    return model.database.connect(file_db)

def extractVideos(filename, config) :
    name = None

    dir_config = config[DIR_CONFIG]
    dir_tasks = config[DIR_TASKS]

    with zipfile.ZipFile(filename) as zf :
        # get task name and create video folder
        name = os.path.dirname(nextOrDefault((x for x in zf.namelist() if x.endswith('/video/')), default='').rstrip('/'))
        if not name: raise Exception()
        dir_task = os.path.join(dir_tasks, name)
        os.makedirs(dir_task, exist_ok=True)
        print(0)

        # extract videos
        videos = (x for x in zf.namelist() if '/video/' in x and ('_capture1.avi' in x or '_capture2.avi' in x))
        zf.extractall(path=dir_tasks, members=videos)
        print(1)

        db = connectFileDb(config)
        gestures = dict(('G{}'.format(x.id), x) for x in model.database.Gesture.select())
        task = model.database.Task(name=name)
        task.save()
        print('task_id:', task.id)
        print(2)

        # open meta file
        meta = nextOrDefault( x for x in zf.namelist() if 'meta_file' in x.lower() )
        if not meta : raise Exception(EXCEPTION_MISSING_META_FILE)
        print(3)
        with zf.open(meta) as file_descriptor_meta :
            print(4)

            #from IPython import embed
            #embed()

            for row in readLinesAsCsv(file_descriptor_meta) :
                print(5)
                video = model.database.Video.new(task.id, row)
                #video.save(force_insert=True)

                file_kinematics = next(x for x in zf.namelist() if '/kinematics/' in x and video.file_name in x)
                with zf.open(file_kinematics) as file_descriptor_kinematics :
                    print(6)
                    frame = 0
                    for row in readLinesAsCsv(file_descriptor_kinematics, delimiter=' ', line_cb=True) :
                        frame += 1
                        kinematic = model.database.Kinematic.new(video.id, frame, row)
                        if (kinematic.id % 10 == 0) :
                            print(7, video.id , kinematic.id)

                db.begin()
                file_transcript = next(x for x in zf.namelist() if '/transcriptions/' in x and video.file_name in x)
                with zf.open(file_transcript) as file_descriptor_transcript :
                    print(8)

                    for row in readLinesAsCsv(file_descriptor_transcript, delimiter=' ') :
                        transcript = model.database.Transcript.new(task.id, video.id, row, gestures)
                        if (transcript.id % 10 == 0) :
                            print(9, video.id , transcript.id)

                db.commit()






    return name