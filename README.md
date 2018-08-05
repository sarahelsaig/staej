**staej** *[steɪd͡ʒ]* is a graphical tool for painlessly navigating and inspecting the [JIGSAWS Dataset](https://cirl.lcsr.jhu.edu/research/hmm/datasets/jigsaws_release/). For a more in-depth look at the purpose of and the technologies in the project please see [the wiki page](https://github.com/DAud-IcI/staej/wiki).

# Package

The application consists of two components. An easy-to-use command line tool for importing the files and the visual interface for working with the imported data. The former is the `enter-staej.py` utility, the latter is the `staej` viewer (`main.py`).

Both are written in Python 3 and primarily tested under Arch Linux. The GUI uses the GTK 3 toolkit (via PyGObject). The dataset is stored locally in SQLite. The JIGSAWS video files are stored uncompressed in the filesystem under the user’s config directory (ie ~/.config/staej on Linux and %APPDATA%\staej on Windows).

# Installation

The application depends on a graphical environment, GTK, Python and many other resources.
* Arch Linux and Windows MSYS2 instructions are in chapter 5 of [the wiki page](https://github.com/DAud-IcI/staej/wiki#5-user-documentation).
* [Ubuntu (18.04, Bionic Beaver) instructions](https://github.com/DAud-IcI/staej/wiki/Install-staej-on-Ubuntu) have their own dedicated page.

## Portability

You can set the APPDATA environment variable to make the distribution portable.

```bash
$ cd staej
$ export APPDATA=$(pwd)
```

# Usage

## enter-staej (enter-staej.py)

```
$ python3 enter-staej.py --help

usage: enter-staej.py [-h] [--db] [zipfile [zipfile ...]]

STAEJ command line interface

positional arguments:

  zipfile         path of the JIGSAWS zip file

optional arguments:

  -h, --help  show this help message and exit

  --db            create or recreate the working SQLite database
```

Examples:
1. `python enter-staej.py jigsaws/*.zip`
    The simplest way to initialize all of the exercises into the database.
2. `python enter-staej.py --db jigsaws/*.zip`
    This will force to re-create the database and overwrite any file created earlier.
3. `python enter-staej.py jigsaws/Suturing.zip`
    When you have additional archives, they are simply added to the database while preserving the existing content.

## staej (main.py)
### 5.2.2 Usage

The application is started with the following command:

```bash
$ python3 main.py
```

Once the window appears the user can select a trial from the tree on the left side, where they are grouped by tasks. Once a video is selected, the rest of the window gets updated:

![main application screenshot][fig7]

Figure 7 . The main screen of staej and the second tab 

1. The video file selector where the available trials are listed
2. The search bar used to filter by video name
3. The Video Info tab shows a selection of general information about the trial as can be seen on the top half of the picture.
4. The Gestures tab can be selected by clicking there.
5. Shows the gesture at the video’s current timestamp.
6. Some generic information about the video.
7. Information about the subject (surgeon) and their ratings on this video.
8. The video is played here and can be controlled with the user interface below.
9. The play/pause (||) button is used to enable or disable playback.
10. The slow forward/backward (<, >) buttons skip one frame (1/30 s) and also pause the playback.
11. The fast forward/backward (<<, >>) buttons skip a whole second but have no effect on whether the video is playing or paused.
12. The kinematics box shows the current state of all kinematic variables at the moment of the currently displayed frame.
13. The Gestures panel is a “playlist” style interface where the user can jump to the beginning of a specific gesture within the video. The start and end

[fig7]: docs/images/image3.png
