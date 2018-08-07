import os
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

# handle Windows / MSYS2 
if sys.platform == "win32" or sys.platform == "msys" :
    os.environ['GDK_WIN32_LAYERED'] = '0'

# check & create software data directory
dir_config = os.path.expandvars('$APPDATA/staej').replace('$APPDATA', os.path.expanduser('~/.config'))
dir_tasks = os.path.join(dir_config, 'tasks')
os.makedirs(dir_tasks, exist_ok=True)

# copy database
file_db = os.path.join(dir_config, 'staej.sqlite')
if not os.path.exists(file_db) :
    print('The database does not exist. Please run enter-staej.py with one or more JIGSAWS zip files as arguments!')
    sys.exit(1)

import handler
handler.start(locals())
