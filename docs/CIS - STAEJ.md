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

## 2.1.1 Surgical Tasks

Throughout exercises the camera was not moved and it was not permitted to use the clutch. Three surgical tasks were recorded:

* Suturing: the subject closes a simulated incision by passing the needle through the material at predetermined points
* Knot-Tying: the subject ties single-tie knot on suture attached to a flexible tube
* Needle-Passing: the subject passes the needle through small metal hoop