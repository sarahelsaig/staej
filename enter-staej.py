import os
import argparse
import shutil

# check & create software data directory
dir_config = os.path.expandvars('$APPDATA/staej').replace('$APPDATA', os.path.expanduser('~/.config'))
dir_tasks = os.path.join(dir_config, 'tasks')
os.makedirs(dir_tasks, exist_ok=True)

# look at arguments
parser = argparse.ArgumentParser(description='STAEJ command line interface')
parser.add_argument('zipfile', nargs='*', help='path of the JIGSAWS zip file')
parser.add_argument('--db', action='store_const', const=True, default=False, help='create or recreate the working SQLite database')
args = parser.parse_args()

# copy database
file_db = os.path.join(dir_config, 'staej.sqlite')
if args.db or not os.path.exists(file_db) :
    shutil.copyfile('template.sqlite', file_db)

# just to get IPython's beautiful exception reports!
#from IPython import embed
#embed()

if len(args.zipfile) > 0 :
    from import_zip import extractVideos
    for file_name in args.zipfile :
        basename = os.path.basename(file_name).rpartition('.')[0]
        try :
            print (basename, ':', 'start')

            name = extractVideos(file_name, globals())

            print (basename, ':', 'done')
        except StopIteration as e:#Exception as e :
            print (basename,':', e);
            import traceback
            traceback.print_exc()
