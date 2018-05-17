staej
=====

A Graphical Tool for Parsing and Inspecting the JIGSAWS Dataset

Dávid El-Saig - O7H8AE

# 1. Introduction

This document is about the application set called **staej** [steɪd͡ʒ].

It contains the description of the JIGSAWS project, a summary of the development history, a user and developer manual for the application and finally a discussion of possible future applications and improvement.

## 1.2. Description

The application consists of two components. An easy-to-use command line tool for importing the files once and the visual interface for working with the imported data. The former is the `enter-staej.py` utility, the latter is the `staej` viewer.

Both are written in Python 3 and primarily tested under Arch Linux. The GUI uses the GTK 3 toolkit (via PyGObject). The dataset is stored locally in SQLite but it’s technically easy to adapt it later for other databases like MySQL, Oracle Database or Microsoft SQL. The JIGSAWS video files are stored uncompressed in the filesystem under the user’s config directory (ie ~/.config/staej on Linux and %APPDATA%\staej on Windows).

The Project is available on GitHub under the MIT license.[1]

# 2. Literature

## 2.1 JHU-ISI Gesture and Skill Assessment Working Set [2]

This paper is about JIGSAWS, a dataset acquired from monitoring three surgical training exercises, that were performed by eight surgeons through multiple iterations. The video and kinematic data was captured using the da Vinci Surgical System (dVSS) using its regular stereo endoscope camera and research interface. This was then extended using a combination of manual annotation and programmatic models. This set was compiled as a collaboration between Johns Hopkins University and Intuitive Surgical Inc (creators of the da Vinci) as part of the larger Language of Surgery project that aims to apply the techniques used for human language analysis to the surgical field.

The stated goal of this project was to study dextrous human motion. This can help us to understand and support the process of skill acquisition, it can aid in developing to better, more objective skill assessing technologies, and to better automation in the field of human-machine collaboration. This type of knowledge can help if the field of surgery by aiding the surgeons in acquiring technical skill, thus reducing the chance of complications.

A follow-up study by some of the same authors reported on several automated segmentation and annotation techniques used on JIGSAWS. [3]

### 2.1.1 Surgical Tasks

Throughout exercises the camera was not moved and it was not permitted to use the clutch. Three surgical tasks were recorded:

* Suturing: the subject closes a simulated incision by passing the needle through the material at predetermined points
* Knot-Tying: the subject ties single-tie knot on suture attached to a flexible tube
* Needle-Passing: the subject passes the needle through small metal hoop

![JIGSAWS screenshots][fig1]
Figure 1. The three surgical tasks in the order they are mentioned above.

### 2.1.2 Subjects and Trials

There were 8 subjects marked with the letters B - I. Their respective experience and skill levels are annotated in the meta file. Each subject repeated every task 5 times, these are called trials. A specific trial is uniquely identified by what the paper calls “TaskUidRep”[1] that follows the `{task}_{subject}00{trial}` format, for example `Knot_Tying_B001`.

> Within staej “TaskUidRep” is simply called file_name, because it’s the video file’s name without the channel “channel1” / ”channel2” suffix and the extension.

### 2.1.3 Kinematics

The kinematic data was captured using the dVSS API at 30Hz, same as the video and they are synchronised, so there is a clear mapping between the video and the kinematics at any point in time. Each record contains four sets of measurements for the two arms on the master side console (left and right master tool manipulators) and the first two patient-side manipulators on the robot. Each set contains:

* 3 variables:        tool tip position (x;y;z)
* 9 variables:        tool tip rotation matrix (R)
* 3 variables:        tool tip linear velocity (x’; y’; z’)
* 3 variables:        tool tip rotational velocity  (α’; β’; γ’)
* 1 variable:        gripper angle velocity (θ)

> This is also the order of columns within staej’s Kinematics table.

### 2.1.4 Annotations

Each of the trials were manually annotated by identifying spans of time when specific atomic units of the surgical activity (“gestures”) were performed. The dataset contains a vocabulary of 15 different gestures. The gestures were designated and identified with the assistance of experienced surgeons. Apart from some empty space in the beginning and end of some videos, each frame was assigned.

The performance of each trial was also annotated by an experienced  gynecologic surgeon using a modified OSATS [3] approach that excluded non-applicable items.

# 3. Related Technologies

## 3.1 The da Vinci Surgical System API [5]

The research interface allows third party developers to monitor the dVSS in real time through a TCP/IP infrastructure. This gives access to the kinematic data as well as user events in real time with the purpose to aid third party developers and researchers in working with the da Vinci. The API server is situated inside the da Vinci System and it’s accessible through standard Ethernet connection.

The kinematic information is sampled at a custom rate specified by the client (between 10 and 100 Hz) and it streams data from the Endoscope Control Manipulator (ECM), the MTMs and the PSMs.

Additionally, the interface transmits asynchronous information, including when the head sensor is triggered, the clutch is pressed or released or when the manipulator arms are swapped. In the JIGSAWS project these were relevant in ensuring the controlled scenario outlined in the previous chapter.

![dVSS API illustration][fig2]
Figure 2. The da Vinci Research interface, also known as the da Vinci Surgical System API

## 3.2 Python [6]

Python is an interpreted, object-oriented, high-level programming language with dynamic semantics created by Guido van Rossum. It has a lot of built-in features and a very convenient package manager called PyPI. It’s free and open source with support for most platforms. It has libraries and bindings for many tasks in the world of science and engineering. I chose this language because of practical reasons, as it is already widely used in robotics for other tasks such as image recognition.

## 3.3 SQLite and Peewee

SQLite is a transactional database engine that is compliant with the SQL standard. As such it has drop-in support with many SQL client libraries, including Peeweee. SQLite has a unique property as it is designed for small scale, self-contained, serverless, zero-configuration applications. Instead of the usual client-server architecture, the entire database is stored as a single file on the hard disk. [7] This is advantageous for the purpose of staej as it makes setup uncomplicated and it can be done purely on userland without administrator intervention. Additionally the command line tool can export the data into SQL file[8], opening the window for simple migration to other SQL-compliant databases (such as MySQL) should the need and opportunity arise.

Peewee was my python ORM of choice. It has built in support for SQLite, MySQL and Postgresql support but it works well with any other Python database driver that’s compliant with the DB-API 2.0 specification. [9] I’ve taken a code-first approach to make the project even less reliant on the specificities of the choice of SQL engine.

> ORM: object-relational mapping tool. A software library that acts as the compatibility layer between the application and the relational database enabling the developer to treat database entities as objects

## 3.4 GObject, GTK+, GStreamer and PyGObject

GObject is the fundamental generic type system at the heart of GLib-based applications (including GTK applications). It’s a C-based object oriented system that is intentionally easy to map onto other languages. It’s distinguishing aspect is its signal system and powerful notification mechanism. [10] It is used by staej indirectly through GTK and GStreamer but also directly through its enhanced MVVM style base class GNotifier.

GTK+ is the widget toolkit used in staej. It was chosen mainly because of its wide platform support and because it’s part of the GLib ecosystem so it can harness all of the power of GObject as well as other libraries like GStreamer.

GStreamer is a pipeline based streaming framework with a modular system and many plug-ins. It is written in C and its elements inherit from GObject. While it’s designed for audio and video it can stream any data[11], although staej only uses it for DivX video. In its current state this project could have used many other video player libraries, but the advantage of GStreamer becomes apparent near the end of this document in chapter 6.1 Future Development. Adding features that require realtime video manipulation is much easier when we have access to the components of the pipeline as in GStreamer.

The previous three are all C libraries, however they are all accessible from Python thanks to the dynamic bindings in the PyGObject library. 

## 3.5 Glade

Glade is a graphical user interface designer that creates XML files in the GtkBuilder format. It provides a language-independent, declarative way to design the user interface and attach events. The Gtk.Builder class is used to import the UI file into GTK+.

# 4. Design

## 4.1 enter-staej

### 4.1.1 Summary

This is the script used to create the SQLite database from the ZIP files in the JIGSAWS distribution. It creates the required directory structure (`enter-staej.py`) and then parses the texts in the archives and extracts the videos into the config directory based on that data (`import_zip.py`).

The CSV parsing logic for the text files is located in the model.database package in the ORM objects used by peewee. Their object structure is equivalent to the database structure seen on the next page.

The main application relies on enter-staej.py to have the database ready. It will display an error message with instructions how to use `enter-staej.py` in that case.

### 4.1.2 Database model

![database structure][fig2]
Figure 3 The database as generated by enter-staej.py
(Kinematic table broken in half to fit page constraints)

## 4.2 staej (main.py)

[fig1]: images/image6.png
[fig2]: images/image2.png
[fig3]: images/image1.png