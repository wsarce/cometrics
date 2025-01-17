import _tkinter
import glob
import json
import os
import pathlib
import pickle
import threading
import time
import traceback
from tkinter import *
from tkinter import filedialog, messagebox, ttk
from tkinter.ttk import Combobox
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from tkvideoutils import VideoRecorder, VideoPlayer
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
# Implement the default Matplotlib key bindings.
from matplotlib.figure import Figure
# Custom library imports
from ttkwidgets import TickScale
from pywoodway.treadmill import SplitBelt, find_treadmills

from session_time_fields import SessionTimeFields
from tkinter_utils import build_treeview, clear_treeview, AddWoodwayProtocolStep, AddBleProtocolStep, \
    CalibrateVibrotactors, CalibrateWoodway, select_focus, scroll_to, EditEventPopup
from ui_params import treeview_bind_tag_dict, treeview_tags, treeview_bind_tags, crossmark, checkmark
from pytactor import VibrotactorArray, VibrotactorArraySide
from pyempatica.empaticae4 import EmpaticaE4, EmpaticaDataStreams, EmpaticaClient, EmpaticaServerConnectError


class OutputViewPanel:
    def __init__(self, caller, parent, x, y, height, width, button_size, ksf,
                 field_font, header_font, video_import_cb, slider_change_cb, config, session_dir,
                 thresholds):
        self.KEY_VIEW, self.E4_VIEW, self.VIDEO_VIEW, self.WOODWAY_VIEW, self.BLE_VIEW = 0, 1, 2, 3, 4
        self.config = config
        self.height, self.width = height, width
        self.x, self.y, self.button_size = x, y, button_size
        self.current_button = 0
        self.view_buttons = []
        self.view_frames = []
        self.time_change_sources = False

        self.frame = Frame(parent, width=width, height=height)
        self.frame.place(x=x, y=y)

        clean_view = Frame(self.frame, width=width,
                           height=button_size[1], bg='white')
        clean_view.place(x=0, y=0)

        key_frame = Frame(parent, width=width, height=height)
        key_frame.place(x=x, y=y + self.button_size[1])
        self.view_frames.append(key_frame)

        video_frame = Frame(parent, width=width, height=height)
        self.view_frames.append(video_frame)

        key_button = Button(self.frame, text="Key Bindings", command=self.switch_key_frame, width=12,
                            font=field_font)
        self.view_buttons.append(key_button)
        self.KEY_VIEW = len(self.view_buttons) - 1
        self.view_buttons[self.KEY_VIEW].place(x=(len(self.view_buttons) - 1) * button_size[0], y=0,
                                               width=button_size[0], height=button_size[1])
        self.view_buttons[self.KEY_VIEW].config(relief=SUNKEN)
        self.key_view = KeystrokeDataFields(self.view_frames[self.KEY_VIEW], ksf,
                                            height=self.height - self.button_size[1], width=self.width,
                                            field_font=field_font, header_font=header_font, button_size=button_size,
                                            caller=caller)

        if self.config.get_e4():
            e4_output_button = Button(self.frame, text="E4 Streams", command=self.switch_e4_frame, width=12,
                                      font=field_font)
            self.view_buttons.append(e4_output_button)
            self.E4_VIEW = len(self.view_buttons) - 1
            self.view_buttons[self.E4_VIEW].place(x=(len(self.view_buttons) - 1) * button_size[0], y=0,
                                                  width=button_size[0], height=button_size[1])
            self.e4_view = ViewE4(self.view_frames[self.E4_VIEW],
                                  height=self.height - self.button_size[1], width=self.width,
                                  field_font=field_font, header_font=header_font, button_size=button_size,
                                  e4_button=e4_output_button)
            e4_frame = Frame(parent, width=width, height=height)
            self.view_frames.append(e4_frame)
        else:
            self.e4_view = None

        if self.config.get_ble():
            self.time_change_sources = False
            ble_output_button = Button(self.frame, text="BLE Input", command=self.switch_ble_frame, width=12,
                                       font=field_font)
            self.view_buttons.append(ble_output_button)
            self.BLE_VIEW = len(self.view_buttons) - 1
            self.view_buttons[self.BLE_VIEW].place(x=(len(self.view_buttons) - 1) * button_size[0], y=0,
                                                   width=button_size[0], height=button_size[1])
            self.ble_view = ViewBLE(self.view_frames[self.BLE_VIEW],
                                    height=self.height - self.button_size[1], width=self.width,
                                    field_font=field_font, header_font=header_font, button_size=button_size,
                                    session_dir=session_dir, ble_thresh=thresholds[0:2],
                                    ble_button=ble_output_button,
                                    config=config, caller=caller)
            ble_frame = Frame(parent, width=width, height=height)
            self.view_frames.append(ble_frame)
        else:
            self.ble_view = None

        if self.config.get_woodway():
            self.time_change_sources = False
            woodway_output_button = Button(self.frame, text="Woodway", command=self.switch_woodway_frame, width=12,
                                           font=field_font)
            self.view_buttons.append(woodway_output_button)
            self.WOODWAY_VIEW = len(self.view_buttons) - 1
            self.view_buttons[self.WOODWAY_VIEW].place(x=(len(self.view_buttons) - 1) * button_size[0], y=0,
                                                       width=button_size[0], height=button_size[1])
            self.woodway_view = ViewWoodway(self.view_frames[self.WOODWAY_VIEW],
                                            height=self.height - self.button_size[1], width=self.width,
                                            field_font=field_font, header_font=header_font, button_size=button_size,
                                            config=config, session_dir=session_dir, woodway_thresh=thresholds[2],
                                            woodway_button=woodway_output_button, caller=caller)
            woodway_frame = Frame(parent, width=width, height=height)
            self.view_frames.append(woodway_frame)
        else:
            self.woodway_view = None

        video_button = Button(self.frame, text="Video View", command=self.switch_video_frame, width=12,
                              font=field_font)
        self.view_buttons.append(video_button)
        self.VIDEO_VIEW = len(self.view_buttons) - 1
        self.view_buttons[self.VIDEO_VIEW].place(x=(len(self.view_buttons) - 1) * button_size[0], y=0,
                                                 width=button_size[0], height=button_size[1])
        self.video_view = ViewVideo(caller, self.view_frames[self.VIDEO_VIEW],
                                    height=self.height - self.button_size[1], width=self.width,
                                    field_font=field_font, header_font=header_font, button_size=button_size,
                                    video_import_cb=video_import_cb, slider_change_cb=slider_change_cb,
                                    fps=self.config.get_fps(), kdf=self.key_view, video_button=video_button)
        self.event_history = []

    def switch_key_frame(self):
        self.switch_frame(self.KEY_VIEW)

    def switch_ble_frame(self):
        self.switch_frame(self.BLE_VIEW)

    def switch_woodway_frame(self):
        self.switch_frame(self.WOODWAY_VIEW)

    def switch_e4_frame(self):
        self.switch_frame(self.E4_VIEW)

    def switch_video_frame(self):
        self.switch_frame(self.VIDEO_VIEW)

    def switch_frame(self, view):
        """
        https://stackoverflow.com/a/23354009
        :param view:
        :return:
        """
        self.view_buttons[self.current_button].config(relief=RAISED)
        self.view_frames[self.current_button].place_forget()
        self.current_button = view
        self.view_buttons[view].config(relief=SUNKEN)
        self.view_frames[view].place(x=self.x, y=self.y + self.button_size[1])

    def close(self):
        if self.e4_view:
            self.e4_view.stop_plot()
            self.e4_view.disconnect_e4()
        if self.video_view:
            if self.video_view.player:
                self.video_view.player.loading = False
            if self.video_view.recorder:
                self.video_view.recorder.stop_recording()
                self.video_view.recorder.stop_playback()
        if self.ble_view:
            self.ble_view.disconnect_ble()
        if self.woodway_view:
            self.woodway_view.disconnect_woodway()

    def start_session(self, recording_path=None):
        if self.e4_view:
            self.e4_view.start_session()
        if self.video_view.recorder:
            self.recording_path = recording_path
            audio_path = os.path.join(pathlib.Path(recording_path).parent, pathlib.Path(recording_path).stem + ".wav")
            self.video_view.recorder.start_recording(video_output=recording_path, audio_output=audio_path)
        if self.ble_view:
            self.ble_view.start_session()
        if self.woodway_view:
            self.woodway_view.start_session()
        if self.video_view:
            self.video_view.clear_event_treeview()
        if self.key_view:
            self.key_view.clear_sh_treeview()

    def enable_video_slider(self):
        if self.video_view.player:
            self.video_view.video_slider.config(state='active')

    def disable_video_slider(self):
        if self.video_view.player:
            self.video_view.video_slider.config(state='disabled')

    def stop_session(self, final_time):
        if self.key_view:
            self.check_duration_keys(final_time)
        if self.e4_view:
            self.e4_view.session_started = False
            self.e4_view.streaming = False
        if self.video_view.recorder:
            self.video_view.recorder.stop_recording()
            self.video_view.recorder.stop_playback()
            self.video_view.recorder.merge_sources(output=self.recording_path,
                                                   ffmpeg_path=os.environ['IMAGEIO_FFMPEG_EXE'])
        if self.woodway_view:
            self.woodway_view.stop_session()
        if self.ble_view:
            self.ble_view.stop_session()

    def check_event(self, key_char, start_time):
        # Make sure it is not None
        if key_char:
            current_frame = None
            current_audio_frame = None
            # Get the current frame of the video if it's playing
            if self.video_view.player:
                current_frame = self.video_view.player.current_frame
                if self.video_view.player.audio_loaded:
                    current_audio_frame = self.video_view.player.audio_index
            elif self.video_view.recorder:
                current_frame = self.video_view.recorder.current_frame
            current_window = None
            # Add the frame and key to the latest E4 window reading if streaming
            if self.e4_view:
                if self.e4_view.e4:
                    current_window = EmpaticaE4.get_unix_timestamp()
            # Get the appropriate key event
            key_events = self.key_view.check_key(key_char, start_time, current_frame, current_window,
                                                 current_audio_frame)
            # Add to session history
            if key_events:
                self.key_view.add_session_event(key_events)
                self.video_view.add_event(key_events)
            else:
                print("INFO: No key events returned")

    def check_duration_keys(self, final_time):
        for i in range(0, len(self.key_view.dur_bindings)):
            if self.key_view.dur_sticky[i]:
                self.check_event(self.key_view.dur_bindings[i][0], final_time)

    def edit_last_event(self):
        self.delete_last_event()
        self.key_view.editing = True
        self.video_view.editing = True

    def delete_last_event(self):
        self.key_view.delete_last_event()
        self.video_view.delete_last_event()

    def undo_last_delete(self):
        self.key_view.undo_last_delete()
        self.video_view.undo_last_delete()

    def get_session_data(self):
        video_data = None
        if self.video_view:
            video_data = self.video_view.video_file
        e4_data = None
        if self.e4_view:
            if self.e4_view.e4:
                e4_data = [
                    self.e4_view.e4.acc_3d,
                    self.e4_view.e4.acc_x,
                    self.e4_view.e4.acc_y,
                    self.e4_view.e4.acc_z,
                    self.e4_view.e4.acc_timestamps,
                    self.e4_view.e4.bvp, self.e4_view.e4.bvp_timestamps,
                    self.e4_view.e4.gsr, self.e4_view.e4.gsr_timestamps,
                    self.e4_view.e4.tmp, self.e4_view.e4.tmp_timestamps,
                    self.e4_view.e4.tag, self.e4_view.e4.tag_timestamps,
                    self.e4_view.e4.ibi, self.e4_view.e4.ibi_timestamps,
                    self.e4_view.e4.bat, self.e4_view.e4.bat_timestamps,
                    self.e4_view.e4.hr, self.e4_view.e4.hr_timestamps
                ]
        ble_prot = None
        if self.ble_view:
            if self.ble_view.protocol_steps:
                ble_prot = self.ble_view.protocol_steps
        woodway_prot = None
        if self.woodway_view:
            if self.woodway_view.protocol_steps:
                woodway_prot = self.woodway_view.protocol_steps
        return self.key_view.event_history, e4_data, video_data, ble_prot, woodway_prot

    def save_session(self, filename, keystrokes):
        if self.e4_view:
            if self.e4_view.windowed_readings:
                try:
                    for keystroke in keystrokes:
                        try:
                            if type(keystroke[1]) is tuple:
                                self.e4_view.windowed_readings[int(keystroke[1][0]) - 1][-1].append(keystroke[0])
                                self.e4_view.windowed_readings[int(keystroke[1][1]) - 1][-1].append(keystroke[0])
                            else:
                                self.e4_view.windowed_readings[int(keystroke[1]) - 1][-1].append(keystroke[0])
                        except Exception as e:
                            print(f"ERROR: Exception encountered:\n{str(e)}\n" + traceback.print_exc())
                    with open(filename, 'wb') as f:
                        pickle.dump(self.e4_view.windowed_readings, f)
                except TypeError as e:
                    with open(filename, 'wb') as f:
                        pickle.dump(self.e4_view.windowed_readings, f)
                    print(f"ERROR: Exception encountered:\n{str(e)}\n" + traceback.print_exc())


class ViewWoodway:
    def __init__(self, parent, height, width, field_font, header_font, button_size, config, session_dir,
                 woodway_button, caller, woodway_thresh=None):
        self.woodway = None
        self.caller = caller
        self.tab_button = woodway_button
        self.session_dir = session_dir
        self.config = config
        self.root = parent
        self.protocol_steps = []
        self.selected_step = 0
        self.load_protocol_thread = None
        self.prot_file = None
        self.step_time = 0
        self.step_duration = 0
        self.woodway_speed_r, self.woodway_speed_l = 0, 0
        self.woodway_incline = 0
        self.session_started = False
        self.changed_protocol = True
        self.__connected = False
        self.paused = False
        if woodway_thresh:
            self.calibrated = True
            self.woodway_thresh = woodway_thresh
            print(f"INFO: Woodway calibrated already - Thresh: {self.woodway_thresh} Calibrated: {self.calibrated}")
        else:
            self.calibrated = False
            self.woodway_thresh = None
            print("INFO: Woodway is not calibrated!")
        # region EXPERIMENTAL PROTOCOL
        element_height_adj = 100
        self.exp_prot_label = Label(parent, text="Experimental Protocol", font=header_font, anchor=CENTER)
        self.exp_prot_label.place(x=int(width * 0.23) + 18, y=10, anchor=N)
        self.prot_treeview_parents = []
        prot_heading_dict = {"#0": ["Duration", 'w', 20, YES, 'w']}
        prot_column_dict = {"1": ["LS", 'c', 1, YES, 'c'],
                            "2": ["RS", 'c', 1, YES, 'c'],
                            "3": ["Incline", 'c', 1, YES, 'c'],
                            "4": ["F", 'c', 50, NO, 'c'],
                            "5": ["D", 'c', 50, NO, 'c']}
        treeview_offset = int(width * 0.03)

        # TODO: When the session is paused the woodway and vibrotactors should stop, equalize speeds first??
        self.prot_treeview, self.prot_filescroll = build_treeview(parent, x=treeview_offset, y=40,
                                                                  height=height - element_height_adj - 40,
                                                                  heading_dict=prot_heading_dict,
                                                                  column_dict=prot_column_dict,
                                                                  width=(int(width * 0.5) - int(width * 0.05)),
                                                                  button_1_bind=self.select_protocol_step,
                                                                  double_bind=self.__edit_protocol_step,
                                                                  button_3_bind=self.__delete_protocol_step)
        self.prot_add_button = Button(parent, text="Add", font=field_font, command=self.__add_protocol_step)
        self.prot_add_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.25)),
                                   y=(height - element_height_adj),
                                   anchor=N,
                                   width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])

        self.woodway_connect_button = Button(parent, text="Connect", font=field_font,
                                             command=self.__connect_to_woodway, bg='#4abb5f')
        self.woodway_connect_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.25)),
                                          y=(height - element_height_adj) + button_size[1] * 2,
                                          anchor=N,
                                          width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])

        self.prot_load_button = Button(parent, text="Load File", font=field_font,
                                       command=self.__load_protocol_from_file)
        self.prot_load_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.25)),
                                    y=(height - element_height_adj) + button_size[1],
                                    anchor=N,
                                    width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])

        self.prot_save_button = Button(parent, text="Save To File", font=field_font,
                                       command=self.__save_protocol_to_file)
        self.prot_save_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.75)),
                                    y=(height - element_height_adj) + button_size[1],
                                    anchor=N,
                                    width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])
        self.prot_save_button['state'] = 'disabled'

        self.prot_del_button = Button(parent, text="Delete", font=field_font,
                                      command=self.__delete_protocol_step)
        self.prot_del_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.75)),
                                   y=(height - element_height_adj),
                                   anchor=N,
                                   width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])

        self.woodway_disconnect_button = Button(parent, text="Disconnect", font=field_font,
                                                command=self.disconnect_woodway, bg='red')
        self.woodway_disconnect_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.75)),
                                             y=(height - element_height_adj) + button_size[1] * 2,
                                             anchor=N,
                                             width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])
        # endregion

        # region BELT CONTROL
        # Vertical sliders speed and inclination for each treadmill
        slider_height_adj = element_height_adj
        self.belt_speed_label = Label(parent, text="Belt Speeds", font=header_font, anchor=CENTER)
        self.belt_speed_label.place(x=int(width * 0.625), y=10, anchor=N)

        self.belt_speed_l_label = Label(parent, text='Left', font=field_font, anchor=CENTER)
        self.belt_speed_l_label.place(x=int(width * 0.575), y=40, anchor=N)

        self.belt_speed_r_label = Label(parent, text='Right', font=field_font, anchor=CENTER)
        self.belt_speed_r_label.place(x=int(width * 0.675), y=40, anchor=N)

        self.belt_speed_l_var = StringVar(parent)
        self.belt_speed_l = Scale(parent, orient="vertical", variable=self.belt_speed_l_var, showvalue=False,
                                  command=self.__write_l_speed, length=int(height * 0.7), from_=29.9, to=-29.9,
                                  digits=3, resolution=0.1)
        self.belt_speed_l.place(x=int(width * 0.575), y=70, anchor=N)

        self.belt_speed_l_value = Label(parent, text="0 MPH", anchor=CENTER, font=field_font)
        self.belt_speed_l_value.place(x=int(width * 0.575), y=80 + int(height * 0.7), anchor=N)

        self.belt_speed_r_var = StringVar(parent)
        self.belt_speed_r = Scale(parent, orient="vertical", variable=self.belt_speed_r_var, showvalue=False,
                                  command=self.__write_r_speed, length=int(height * 0.7), from_=29.9, to=-29.9,
                                  digits=3, resolution=0.1)
        self.belt_speed_r.place(x=int(width * 0.675), y=70, anchor=N)
        self.belt_speed_r_value = Label(parent, text="0 MPH", anchor=CENTER, font=field_font)
        self.belt_speed_r_value.place(x=int(width * 0.675), y=80 + int(height * 0.7), anchor=N)

        # This section gets 25% of the panel
        self.belt_incline_label = Label(parent, text="Belt Incline", font=header_font, anchor=CENTER)
        self.belt_incline_label.place(x=int(width * 0.875), y=10, anchor=N)

        self.belt_incline_l_var = StringVar(parent)
        self.belt_incline_l = Scale(parent, orient="vertical", variable=self.belt_incline_l_var, showvalue=False,
                                    command=self.__write_incline, length=int(height * 0.7), from_=29.9, to=0,
                                    digits=3, resolution=0.1)
        self.belt_incline_l.place(x=int(width * 0.875), y=70, anchor=N)

        self.belt_incline_l_value = Label(parent, text="0\u00b0", anchor=CENTER, font=field_font)
        self.belt_incline_l_value.place(x=int(width * 0.875), y=80 + int(height * 0.7), anchor=N)

        self.calibrate_button = Button(parent, text='Calibrate Woodway Threshold', font=field_font,
                                       command=self.__calibrate_woodway)
        self.calibrate_button.place(x=int(width * 0.75), y=(height - element_height_adj) + button_size[1] * 2,
                                    anchor=N,
                                    width=int(width * 0.45), height=button_size[1])

        self.__disable_ui_elements()
        # endregion

        self.woodway_dir = os.path.join(self.session_dir, "Woodway")
        if os.path.exists(self.woodway_dir):
            try:
                latest_protocol = max(pathlib.Path(self.woodway_dir).glob("*.json"), key=lambda f: f.stat().st_ctime)
                self.__load_protocol_from_file(latest_protocol)
            except ValueError:
                print("WARNING: Protocol folder exists with no protocols!")

    def disable_ui_elements(self):
        self.__disable_ui_elements()
        # self.prot_add_button.config(state='disabled')
        # self.prot_del_button.config(state='disabled')
        # self.prot_save_button.config(state='disabled')
        # self.prot_load_button.config(state='disabled')
        self.calibrate_button.config(state='disabled')

    def __enable_connect_button(self):
        self.woodway_connect_button.config(state='active')

    def __disable_ui_elements(self):
        self.belt_incline_l.config(state='disabled')
        self.belt_speed_l.config(state='disabled')
        self.belt_speed_r.config(state='disabled')
        self.woodway_disconnect_button.config(state='disabled')

    def __enable_ui_elements(self):
        self.belt_incline_l.config(state='active')
        self.belt_speed_l.config(state='active')
        self.belt_speed_r.config(state='active')
        self.woodway_disconnect_button.config(state='active')
        self.woodway_connect_button.config(state='disabled')

    def get_calibration_thresholds(self):
        if not self.is_calibrated():
            raise ValueError("Woodway are not calibrated!")
        else:
            self.woodway_speed_l, self.woodway_speed_r = self.woodway_thresh, self.woodway_thresh
            return self.woodway_thresh

    def start_session(self):
        self.session_started = True
        self.woodway.belt_a.set_speed(self.woodway_speed_l)
        self.woodway.belt_b.set_speed(self.woodway_speed_r)
        self.__save_protocol_to_file()

    def stop_session(self):
        if self.woodway:
            self.session_started = False
            self.disconnect_woodway()

    def next_protocol_step(self, current_time):
        if self.selected_step >= len(self.protocol_steps):
            return
        if current_time == 1:
            self.selected_step = 0
            self.__update_woodway_protocol()
        if (self.step_time - current_time) == 0:
            self.selected_step += 1
            self.__update_woodway_protocol()

    def pause_woodway(self):
        if self.session_started:
            self.belt_speed_l.set(0.0)
            self.belt_speed_r.set(0.0)
        if self.woodway:
            self.belt_speed_l_value.config(text=f"{float(0.0):.1f} MPH")
            self.belt_speed_r_value.config(text=f"{float(0.0):.1f} MPH")
            self.woodway.set_speed(0.0, 0.0)
        self.__write_incline(0.0)
        self.paused = True

    def start_woodway(self):
        self.paused = False
        self.__update_woodway()

    def __update_woodway_protocol(self):
        if self.selected_step >= len(self.protocol_steps):
            self.woodway_speed_l = 0.0
            self.woodway_speed_r = 0.0
            self.woodway_incline = 0.0
            self.__update_woodway()
            return
        self.selected_command = self.protocol_steps[self.selected_step]
        self.step_duration = self.selected_command[0]
        self.step_time += self.step_duration
        self.woodway_speed_l = self.woodway_thresh + self.selected_command[1]
        self.woodway_speed_r = self.woodway_thresh + self.selected_command[2]
        self.woodway_incline += self.selected_command[3]
        self.__update_woodway()
        select_focus(self.prot_treeview, self.prot_treeview_parents[self.selected_step])
        scroll_to(self.prot_treeview, self.selected_step)
        if self.config.get_protocol_beep():
            SessionTimeFields.beep()
        if self.selected_command[4] != '':
            self.caller.handle_key_press(self.selected_command[4])
        if self.selected_command[5] != '':
            self.caller.handle_key_press(self.selected_command[5])

    def __update_woodway(self):
        self.__write_incline(self.woodway_incline)
        self.__write_speed()

    def is_connected(self):
        return self.__connected

    def is_calibrated(self):
        return self.calibrated

    def calibrate_return(self, woodway_threshold):
        self.calibrated = True
        self.woodway_thresh = woodway_threshold

    def __calibrate_woodway(self):
        if self.woodway:
            if self.woodway.is_connected():
                CalibrateWoodway(self, self.root, self.woodway)
            else:
                messagebox.showerror("Error",
                                     "Something went wrong connecting to the Woodway!\nCannot be calibrated!")
                self.tab_button['text'] = 'Woodway' + crossmark
        else:
            messagebox.showerror("Error", "Connect to Woodway first!\nCannot be calibrated!")
            self.tab_button['text'] = 'Woodway' + crossmark

    def select_protocol_step(self, event):
        selection = self.prot_treeview.identify_row(event.y)
        if selection:
            self.selected_step = int(selection)

    def populate_protocol_steps(self):
        if self.protocol_steps:
            for i in range(0, len(self.protocol_steps)):
                self.prot_treeview_parents.append(
                    self.prot_treeview.insert("", 'end', str(i + 1), text=str(self.protocol_steps[i][0]),
                                              values=(self.protocol_steps[i][1], self.protocol_steps[i][2],
                                                      self.protocol_steps[i][3], self.protocol_steps[i][4],
                                                      self.protocol_steps[i][5]),
                                              tags=(treeview_tags[(i + 1) % 2])))

    def __heal_legacy_protocol(self):
        for step in self.protocol_steps:
            if len(step) == 4:
                step.extend(['', ''])
        with open(self.prot_file, 'w') as f:
            x = {"Steps": self.protocol_steps}
            json.dump(x, f)

    def __load_protocol_from_file(self, selected_file=None):
        try:
            if selected_file:
                self.selected_step = 0
                self.prot_file = selected_file
                with open(self.prot_file, 'r') as f:
                    self.protocol_steps = json.load(f)['Steps']
                if len(self.protocol_steps[0]) == 4:
                    self.__heal_legacy_protocol()
                self.repopulate_treeview()
            else:
                selected_file = filedialog.askopenfilename(filetypes=(("JSON Files", "*.json"),))
                if selected_file:
                    self.selected_step = 0
                    self.prot_file = selected_file
                    with open(self.prot_file, 'r') as f:
                        self.protocol_steps = json.load(f)['Steps']
                    if len(self.protocol_steps[0]) == 4:
                        self.__heal_legacy_protocol()
                    self.repopulate_treeview()
                    self.changed_protocol = True
                    self.prot_save_button['state'] = 'active'
                else:
                    messagebox.showwarning("Warning", "No file selected, please try again!")
                    self.tab_button['text'] = 'Woodway' + checkmark
        except Exception as ex:
            messagebox.showerror("Exception Encountered", f"Error encountered when loading protocol file!\n{str(ex)}")
            self.tab_button['text'] = 'Woodway' + crossmark

    def __save_protocol_to_file(self):
        try:
            if self.changed_protocol:
                if self.prot_file:
                    file_dir = os.path.join(self.session_dir, "Woodway")
                    if not os.path.exists(file_dir):
                        os.mkdir(file_dir)
                    if pathlib.Path(self.prot_file).parent != file_dir:
                        self.prot_file = os.path.join(file_dir, pathlib.Path(self.prot_file).name)
                    file_count = len(glob.glob1(file_dir, "*.json"))
                    if file_count > 0:
                        new_file = os.path.join(pathlib.Path(self.prot_file).parent,
                                                '_'.join(pathlib.Path(self.prot_file).stem.split('_')[
                                                         :-1]) + f"_V{file_count}.json")
                    else:
                        new_file = os.path.join(pathlib.Path(self.prot_file).parent,
                                                pathlib.Path(self.prot_file).stem + f"_V{file_count}.json")
                    with open(new_file, 'w') as f:
                        x = {"Steps": self.protocol_steps}
                        json.dump(x, f)
                    self.__load_protocol_from_file(selected_file=new_file)
                    self.changed_protocol = False
                    self.prot_save_button['state'] = 'disabled'
                else:
                    file_dir = os.path.join(self.session_dir, "Woodway")
                    if not os.path.exists(file_dir):
                        os.mkdir(file_dir)
                    new_file = os.path.join(file_dir, "woodway_protocol.json")
                    if new_file:
                        self.prot_file = new_file
                        with open(self.prot_file, 'w') as f:
                            x = {"Steps": self.protocol_steps}
                            json.dump(x, f)
                        self.changed_protocol = False
                        self.prot_save_button['state'] = 'disabled'
                    else:
                        messagebox.showwarning("Warning", "No filename supplied! Can't save, please try again!")
        except Exception as ex:
            messagebox.showerror("Exception Encountered", f"Error encountered when saving protocol file!\n{str(ex)}")

    def popup_return(self, new_step, edit=False):
        if edit:
            if self.selected_step:
                self.protocol_steps[int(self.selected_step) - 1] = new_step
                self.repopulate_treeview()
        else:
            self.protocol_steps.append(new_step)
            self.repopulate_treeview()
        self.changed_protocol = True
        self.prot_save_button['state'] = 'active'

    def repopulate_treeview(self):
        clear_treeview(self.prot_treeview)
        self.prot_treeview_parents = []
        self.populate_protocol_steps()

    def __edit_protocol_step(self, event):
        if self.selected_step:
            step = self.protocol_steps[int(self.selected_step) - 1]
            AddWoodwayProtocolStep(self, self.root, edit=True, dur=step[0], ls=step[1], rs=step[2], incl=step[3],
                                   freq_key=step[4], dur_key=step[5])

    def __add_protocol_step(self):
        AddWoodwayProtocolStep(self, self.root)

    def __delete_protocol_step(self, event=None):
        if self.selected_step:
            self.protocol_steps.pop(self.selected_step - 1)
            self.repopulate_treeview()
            self.changed_protocol = True
            self.prot_save_button['state'] = 'active'

    def __connect_to_woodway(self):
        try:
            a_port, b_port = find_treadmills(a_sn=self.config.get_woodway_a(), b_sn=self.config.get_woodway_b())
            if a_port and b_port:
                self.woodway = SplitBelt(b_port.name, a_port.name)
                self.woodway.start_belts(True, False, True, False)
                self.__enable_ui_elements()
                self.__connected = True
                messagebox.showinfo("Success!", "Woodway Split Belt treadmill connected!")
                self.tab_button['text'] = 'Woodway' + checkmark
            else:
                messagebox.showerror("Error", "No treadmills found! Check serial numbers and connections!")
                self.tab_button['text'] = 'Woodway' + crossmark
        except Exception as ex:
            messagebox.showerror("Exception Encountered",
                                 f"Encountered exception when connecting to Woodway!\n{str(ex)}")
            self.tab_button['text'] = 'Woodway' + crossmark

    def disconnect_woodway(self):
        if self.woodway:
            self.woodway.stop_belts()
            self.woodway.set_elevations(float(0.0))
            self.woodway.close()
            self.woodway = None
            self.__disable_ui_elements()
            self.__enable_connect_button()
            self.__connected = False
            self.tab_button['text'] = 'Woodway'

    def __write_speed(self):
        if self.session_started:
            self.belt_speed_l.set(self.woodway_speed_l)
            self.belt_speed_r.set(self.woodway_speed_r)
        if self.woodway:
            self.belt_speed_l_value.config(text=f"{float(self.woodway_speed_l):.1f} MPH")
            self.belt_speed_r_value.config(text=f"{float(self.woodway_speed_r):.1f} MPH")
            self.woodway.set_speed(self.woodway_speed_l, self.woodway_speed_r)

    def __write_l_speed(self, speed):
        if self.session_started:
            self.belt_speed_l.set(float(speed))
        if self.woodway:
            self.belt_speed_l_value.config(text=f"{float(speed):.1f} MPH")
            self.woodway.belt_a.set_speed(float(speed))

    def __write_r_speed(self, speed):
        if self.session_started:
            self.belt_speed_r.set(float(speed))
        if self.woodway:
            self.belt_speed_r_value.config(text=f"{float(speed):.1f} MPH")
            self.woodway.belt_b.set_speed(float(speed))

    def __write_incline(self, incline):
        if self.session_started:
            self.belt_incline_l.set(float(incline))
        if self.woodway:
            self.belt_incline_l_value.config(text=f"{float(incline):.1f}\u00b0")
            self.woodway.set_elevations(float(incline))


class ViewBLE:
    def __init__(self, parent, height, width, field_font, header_font, button_size,
                 session_dir, ble_button, config, caller, ble_thresh=None):
        self.root = parent
        self.caller = caller
        self.config = config
        self.tab_button = ble_button
        self.session_dir = session_dir
        self.ble_instance = VibrotactorArray.get_ble_instance()
        self.left_vta, self.right_vta = None, None
        self.ble_connect_thread = None
        self.protocol_steps = []
        self.selected_step = 0
        self.prot_file = None
        self.step_duration = 0
        self.step_time = 0
        self.session_started = False
        self.changed_protocol = True
        self.__connected = False
        self.paused = False
        self.r_ble_1_3_value, self.r_ble_4_6_value, self.r_ble_7_9_value, self.r_ble_10_12_value = 0, 0, 0, 0
        self.l_ble_1_3_value, self.l_ble_4_6_value, self.l_ble_7_9_value, self.l_ble_10_12_value = 0, 0, 0, 0
        if ble_thresh[0] and ble_thresh[1]:
            self.calibrated = True
            self.right_ble_thresh = ble_thresh[0]
            self.left_ble_thresh = ble_thresh[1]
            print(
                f"INFO: Vibrotactors already calibrated - Right: {self.right_ble_thresh} Left: {self.left_ble_thresh} "
                f"Calibrated: {self.calibrated}")
        else:
            self.calibrated = False
            self.right_ble_thresh = None
            self.left_ble_thresh = None
            print("INFO: Vibrotactors not calibrated!")
        # region EXPERIMENTAL PROTOCOL
        element_height_adj = 100
        self.exp_prot_label = Label(parent, text="Experimental Protocol", font=header_font, anchor=CENTER)
        self.exp_prot_label.place(x=int(width * 0.23) + 18, y=10, anchor=N)
        self.prot_treeview_parents = []
        prot_heading_dict = {"#0": ["Duration", 'w', 20, YES, 'w']}
        prot_column_dict = {"1": ["Left", 'c', 1, YES, 'c'],
                            "2": ["Right", 'c', 1, YES, 'c'],
                            "3": ["F", 'c', 50, NO, 'c'],
                            "4": ["D", 'c', 50, NO, 'c']}
        treeview_offset = int(width * 0.03)
        self.prot_treeview, self.prot_filescroll = build_treeview(parent, x=treeview_offset, y=40,
                                                                  height=height - element_height_adj - 40,
                                                                  heading_dict=prot_heading_dict,
                                                                  column_dict=prot_column_dict,
                                                                  width=(int(width * 0.5) - int(width * 0.05)),
                                                                  button_1_bind=self.select_protocol_step,
                                                                  double_bind=self.__edit_protocol_step,
                                                                  button_3_bind=self.__delete_protocol_step)

        self.prot_add_button = Button(parent, text="Add", font=field_font, command=self.__add_protocol_step)
        self.prot_add_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.25)),
                                   y=(height - element_height_adj),
                                   anchor=N,
                                   width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])

        self.ble_connect_button = Button(parent, text="Connect", font=field_font,
                                         command=self.__connect_to_ble, bg='#4abb5f')
        self.ble_connect_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.25)),
                                      y=(height - element_height_adj) + button_size[1] * 2,
                                      anchor=N,
                                      width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])

        self.prot_load_button = Button(parent, text="Load File", font=field_font,
                                       command=self.__load_protocol_from_file)
        self.prot_load_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.25)),
                                    y=(height - element_height_adj) + button_size[1],
                                    anchor=N,
                                    width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])

        self.prot_save_button = Button(parent, text="Save To File", font=field_font,
                                       command=self.__save_protocol_to_file)
        self.prot_save_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.75)),
                                    y=(height - element_height_adj) + button_size[1],
                                    anchor=N,
                                    width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])
        self.prot_save_button['state'] = 'disabled'

        self.prot_del_button = Button(parent, text="Delete", font=field_font,
                                      command=self.__delete_protocol_step)
        self.prot_del_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.75)),
                                   y=(height - element_height_adj),
                                   anchor=N,
                                   width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])

        self.ble_disconnect_button = Button(parent, text="Disconnect", font=field_font,
                                            command=self.disconnect_ble, bg='red')
        self.ble_disconnect_button.place(x=(treeview_offset + ((int(width * 0.5) - int(width * 0.05)) * 0.75)),
                                         y=(height - element_height_adj) + button_size[1] * 2,
                                         anchor=N,
                                         width=(int(width * 0.5) - int(width * 0.05)) / 2, height=button_size[1])
        # endregion

        # region VIBROTACTOR SLIDERS
        slider_vars = [
            (self.update_ble_1, IntVar(parent)),
            (self.update_ble_2, IntVar(parent)),
            (self.update_ble_3, IntVar(parent)),
            (self.update_ble_4, IntVar(parent)),
            (self.update_ble_5, IntVar(parent)),
            (self.update_ble_6, IntVar(parent)),
            (self.update_ble_7, IntVar(parent)),
            (self.update_ble_8, IntVar(parent)),
            (self.update_ble_9, IntVar(parent)),
            (self.update_ble_10, IntVar(parent)),
            (self.update_ble_11, IntVar(parent)),
            (self.update_ble_12, IntVar(parent)),
            (self.update_frequency, IntVar(parent))
        ]
        self.slider_objects = []

        slider_separation = int((width * 0.4) / 6)
        slider_separation_h = 40
        slider_count = 0

        label = Label(parent, text="Vibrotactor Control", font=header_font, anchor=N)
        label.place(x=int(width * 0.60) - slider_separation + int(slider_separation * 3), y=10, anchor=N)
        for i in range(0, 12):
            if i == 6:
                slider_count = 0
                slider_separation_h += int(height * 0.4)
            label = Label(parent, text=f"{i + 1}", font=field_font, anchor=N, width=4)
            label.place(x=int(width * 0.6) + int(slider_count * slider_separation), y=slider_separation_h, anchor=N)
            temp_slider = Scale(parent, orient="vertical", variable=slider_vars[i][1], showvalue=False,
                                command=slider_vars[i][0], length=int(height * 0.35), from_=255, to=0)
            temp_slider.place(x=int(width * 0.6) + int(slider_count * slider_separation), y=slider_separation_h + 25,
                              anchor=N)
            self.slider_objects.append(temp_slider)
            slider_count += 1
        slider_separation_h = 40
        label = Label(parent, text="Freq", font=field_font, anchor=CENTER, width=6)
        label.place(x=int(width * 0.60) - slider_separation, y=slider_separation_h, anchor=N)
        self.freq_slider = Scale(parent, orient="vertical", variable=slider_vars[12][1], showvalue=False,
                                 command=slider_vars[12][0], length=int(height * 0.75), from_=7, to=0)
        self.freq_slider.place(x=int(width * 0.60) - slider_separation, y=slider_separation_h + 25, anchor=N)

        self.calibrate_button = Button(parent, text='Calibrate Vibrotactor Threshold', font=field_font,
                                       command=self.__calibrate_ble)
        self.calibrate_button.place(x=int(width * 0.75), y=(height - element_height_adj) + button_size[1] * 2,
                                    anchor=N,
                                    width=int(width * 0.45), height=button_size[1])

        self.__disable_ui_elements()
        self.ble_dir = os.path.join(self.session_dir, "BLE")
        if os.path.exists(self.ble_dir):
            try:
                latest_protocol = max(pathlib.Path(self.ble_dir).glob("*.json"), key=lambda f: f.stat().st_ctime)
                self.__load_protocol_from_file(latest_protocol)
            except ValueError:
                print("WARNING: Protocol folder exists with no protocols!")
        # endregion

    def __enable_ui_elements(self):
        self.ble_connect_button.config(state='disabled')
        self.ble_disconnect_button.config(state='active')
        self.freq_slider.config(state='active')
        for slider in self.slider_objects:
            slider.config(state='active')

    def disable_ui_elements(self):
        for slider in self.slider_objects:
            slider.config(state='active')
        self.ble_disconnect_button.config(state='disabled')
        # self.prot_add_button.config(state='disabled')
        # self.prot_del_button.config(state='disabled')
        # self.prot_save_button.config(state='disabled')
        # self.prot_load_button.config(state='disabled')
        self.calibrate_button.config(state='disabled')

    def __enable_connect_button(self):
        self.ble_connect_button.config(state='active')

    def __disable_ui_elements(self):
        self.ble_disconnect_button.config(state='disabled')
        self.__enable_connect_button()
        self.freq_slider.config(state='disabled')
        for slider in self.slider_objects:
            slider.config(state='disabled')

    def get_calibration_thresholds(self):
        if not self.is_calibrated():
            raise ValueError("Vibrotactors are not calibrated!")
        else:
            self.r_ble_1_3_value = self.right_ble_thresh
            self.r_ble_4_6_value = self.right_ble_thresh
            self.r_ble_7_9_value = self.right_ble_thresh
            self.r_ble_10_12_value = self.right_ble_thresh
            self.l_ble_1_3_value = self.left_ble_thresh
            self.l_ble_4_6_value = self.left_ble_thresh
            self.l_ble_7_9_value = self.left_ble_thresh
            self.l_ble_10_12_value = self.left_ble_thresh
            return self.right_ble_thresh, self.left_ble_thresh

    def start_session(self):
        self.session_started = True
        self.right_vta.write_all_motors(self.right_ble_thresh)
        self.left_vta.write_all_motors(self.left_ble_thresh)
        self.right_vta.start_imu()
        self.left_vta.start_imu()
        self.__save_protocol_to_file()

    def stop_session(self):
        self.session_started = False
        self.right_vta.stop_imu()
        self.left_vta.stop_imu()
        self.disconnect_ble()

    def is_connected(self):
        return self.__connected

    def is_calibrated(self):
        return self.calibrated

    def calibrate_return(self, left_threshold, right_threshold):
        self.calibrated = True
        self.left_ble_thresh = left_threshold
        self.right_ble_thresh = right_threshold

    def __calibrate_ble(self):
        if self.right_vta and self.left_vta:
            if self.right_vta.is_connected() and self.left_vta.is_connected():
                CalibrateVibrotactors(self, self.root, self.left_vta, self.right_vta)
            else:
                messagebox.showerror("Error",
                                     "Something went wrong connecting to the vibrotactors!\nCannot be calibrated!")
                self.tab_button['text'] = 'BLE Input' + crossmark
        else:
            messagebox.showerror("Error", "Connect to vibrotactors first!\nCannot be calibrated!")

    def __edit_protocol_step(self, event):
        if self.selected_step:
            step = self.protocol_steps[int(self.selected_step) - 1]
            AddBleProtocolStep(self, self.root, edit=True, dur=step[0],
                               motor_1=step[1], motor_2=step[2], freq_key=step[3], dur_key=step[4])

    def next_protocol_step(self, current_time):
        if self.selected_step >= len(self.protocol_steps):
            return
        if current_time == 1:
            self.selected_step = 0
            self.__update_ble_protocol()
        if (self.step_time - current_time) == 0:
            self.selected_step += 1
            self.__update_ble_protocol()

    def pause_ble(self):
        for slider in self.slider_objects:
            slider.set(0.0)
        self.right_vta.write_all_motors(int(0.0))
        self.left_vta.write_all_motors(int(0.0))
        self.paused = True

    def start_ble(self):
        self.paused = False
        self.__update_ble()

    def __update_ble_protocol(self):
        if self.selected_step >= len(self.protocol_steps):
            self.r_ble_1_3_value = 0
            self.l_ble_1_3_value = 0
            self.__update_ble()
            return
        self.selected_command = self.protocol_steps[self.selected_step]
        self.step_duration = self.selected_command[0]
        self.step_time += self.step_duration
        self.r_ble_1_3_value = (self.selected_command[1] / 100) * self.right_ble_thresh
        self.l_ble_1_3_value = (self.selected_command[2] / 100) * self.left_ble_thresh
        self.__update_ble()
        select_focus(self.prot_treeview, self.prot_treeview_parents[self.selected_step])
        scroll_to(self.prot_treeview, self.selected_step)
        if self.config.get_protocol_beep():
            SessionTimeFields.beep()
        if self.selected_command[3] != '':
            self.caller.handle_key_press(self.selected_command[3])
        if self.selected_command[4] != '':
            self.caller.handle_key_press(self.selected_command[4])

    def __update_ble(self):
        for slider in self.slider_objects:
            slider.set(self.l_ble_1_3_value)
        self.right_vta.write_all_motors(int(self.r_ble_1_3_value))
        self.left_vta.write_all_motors(int(self.l_ble_1_3_value))

    def select_protocol_step(self, event):
        selection = self.prot_treeview.identify_row(event.y)
        if selection:
            self.selected_step = int(selection)

    def populate_protocol_steps(self):
        if self.protocol_steps:
            for i in range(0, len(self.protocol_steps)):
                self.prot_treeview_parents.append(
                    self.prot_treeview.insert("", 'end', str(i + 1), text=str(self.protocol_steps[i][0]),
                                              values=(self.protocol_steps[i][1], self.protocol_steps[i][2],
                                                      self.protocol_steps[i][3], self.protocol_steps[i][4]),
                                              tags=(treeview_tags[(i + 1) % 2])))

    def __heal_legacy_protocol(self):
        for step in self.protocol_steps:
            if len(step) == 3:
                step.extend(['', ''])
        with open(self.prot_file, 'w') as f:
            x = {"Steps": self.protocol_steps}
            json.dump(x, f)

    def __load_protocol_from_file(self, selected_file=None):
        try:
            if selected_file:
                self.selected_step = 0
                self.prot_file = selected_file
                with open(self.prot_file, 'r') as f:
                    self.protocol_steps = json.load(f)['Steps']
                if len(self.protocol_steps[0]) == 3:
                    self.__heal_legacy_protocol()
                self.repopulate_treeview()
            else:
                selected_file = filedialog.askopenfilename(filetypes=(("JSON Files", "*.json"),))
                if selected_file:
                    self.selected_step = 0
                    self.prot_file = selected_file
                    with open(self.prot_file, 'r') as f:
                        self.protocol_steps = json.load(f)['Steps']
                    self.repopulate_treeview()
                    self.changed_protocol = True
                    self.prot_save_button['state'] = 'active'
                else:
                    messagebox.showwarning("Warning", "No file selected, please try again!")
        except Exception as ex:
            messagebox.showerror("Exception Encountered", f"Error encountered when loading protocol file!\n{str(ex)}")
            self.tab_button['text'] = 'BLE Input' + crossmark

    def __load_protocol(self, file):
        self.prot_file = file
        self.protocol_steps = json.loads(self.prot_file)

    def popup_return(self, new_step, edit=False):
        if edit:
            if self.selected_step:
                self.protocol_steps[int(self.selected_step) - 1] = new_step
                self.repopulate_treeview()
        else:
            self.protocol_steps.append(new_step)
            self.repopulate_treeview()
        self.changed_protocol = True
        self.prot_save_button['state'] = 'active'

    def repopulate_treeview(self):
        clear_treeview(self.prot_treeview)
        self.prot_treeview_parents = []
        self.populate_protocol_steps()

    def __add_protocol_step(self):
        AddBleProtocolStep(self, self.root)

    def __delete_protocol_step(self, event=None):
        if self.selected_step:
            self.protocol_steps.pop(self.selected_step - 1)
            self.repopulate_treeview()
            self.changed_protocol = True
            self.prot_save_button['state'] = 'active'

    def __save_protocol_to_file(self):
        try:
            if self.changed_protocol:
                if self.prot_file:
                    file_dir = os.path.join(self.session_dir, "BLE")
                    if not os.path.exists(file_dir):
                        os.mkdir(file_dir)
                    if pathlib.Path(self.prot_file).parent != file_dir:
                        self.prot_file = os.path.join(file_dir, pathlib.Path(self.prot_file).name)
                    file_count = len(glob.glob1(file_dir, "*.json"))
                    if file_count > 0:
                        new_file = os.path.join(pathlib.Path(self.prot_file).parent,
                                                '_'.join(pathlib.Path(self.prot_file).stem.split('_')[
                                                         :-1]) + f"_V{file_count}.json")
                    else:
                        new_file = os.path.join(pathlib.Path(self.prot_file).parent,
                                                pathlib.Path(self.prot_file).stem + f"_V{file_count}.json")
                    with open(new_file, 'w') as f:
                        x = {"Steps": self.protocol_steps}
                        json.dump(x, f)
                    self.__load_protocol_from_file(selected_file=new_file)
                    self.changed_protocol = False
                    self.prot_save_button['state'] = 'disabled'
                else:
                    file_dir = os.path.join(self.session_dir, "BLE")
                    if not os.path.exists(file_dir):
                        os.mkdir(file_dir)
                    new_file = os.path.join(file_dir, "ble_protocol.json")
                    if new_file:
                        self.prot_file = new_file
                        with open(self.prot_file, 'w') as f:
                            x = {"Steps": self.protocol_steps}
                            json.dump(x, f)
                        self.changed_protocol = False
                        self.prot_save_button['state'] = 'disabled'
                    else:
                        messagebox.showwarning("Warning", "No filename supplied! Can't save, please try again!")
        except Exception as ex:
            messagebox.showerror("Exception Encountered", f"Error encountered when saving protocol file!\n{str(ex)}")
            self.tab_button['text'] = 'BLE Input' + crossmark

    def disconnect_ble(self):
        VibrotactorArray.disconnect_ble_devices(self.ble_instance)
        self.__disable_ui_elements()
        self.__connected = False
        self.tab_button['text'] = 'BLE Input'

    def __connect_to_ble(self):
        self.ble_connect_thread = threading.Thread(target=self.__connect_ble_thread)
        self.ble_connect_thread.daemon = 1
        self.ble_connect_thread.start()

    def __connect_ble_thread(self):
        while True:
            try:
                left_vta = VibrotactorArray(self.ble_instance)
                right_vta = VibrotactorArray(self.ble_instance)
                if left_vta.is_connected() and left_vta.is_connected():
                    print(f"INFO: VTA Left - {left_vta.get_side()} VTA Right - {right_vta.get_side()}")
                    if left_vta.get_side() != VibrotactorArraySide.LEFT:
                        self.left_vta = right_vta
                        self.right_vta = left_vta
                    else:
                        self.left_vta = left_vta
                        self.right_vta = right_vta
                    print(f"INFO: VTA Left - {self.left_vta.get_side()} VTA Right - {self.right_vta.get_side()}")
                    self.__enable_ui_elements()
                    messagebox.showinfo("Success!", "Vibrotactor arrays are connected!")
                    self.__connected = True
                    self.tab_button['text'] = 'BLE Input' + checkmark
                    break
                else:
                    response = messagebox.askyesno("Error", "Could not connect to both vibrotactor arrays!\nTry again?")
                    if not response:
                        break
            except Exception as ex:
                messagebox.showerror("Error", f"Exception encountered:\n{str(ex)}")
                self.tab_button['text'] = 'BLE Input' + crossmark

    def update_frequency(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.set_motor_frequency(int(value))
            self.left_vta.set_motor_frequency(int(value))

    def update_ble_1(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(0, int(value))
            self.left_vta.write_motor_level(0, int(value))

    def update_ble_2(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(1, int(value))
            self.left_vta.write_motor_level(1, int(value))

    def update_ble_3(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(2, int(value))
            self.left_vta.write_motor_level(2, int(value))

    def update_ble_4(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(3, int(value))
            self.left_vta.write_motor_level(3, int(value))

    def update_ble_5(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(4, int(value))
            self.left_vta.write_motor_level(4, int(value))

    def update_ble_6(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(5, int(value))
            self.left_vta.write_motor_level(5, int(value))

    def update_ble_7(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(6, int(value))
            self.left_vta.write_motor_level(6, int(value))

    def update_ble_8(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(7, int(value))
            self.left_vta.write_motor_level(7, int(value))

    def update_ble_9(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(8, int(value))
            self.left_vta.write_motor_level(8, int(value))

    def update_ble_10(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(9, int(value))
            self.left_vta.write_motor_level(9, int(value))

    def update_ble_11(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(10, int(value))
            self.left_vta.write_motor_level(10, int(value))

    def update_ble_12(self, value):
        if self.right_vta and self.left_vta:
            self.right_vta.write_motor_level(11, int(value))
            self.left_vta.write_motor_level(11, int(value))


class ViewVideo:
    def __init__(self, caller, root, height, width, field_font, header_font, button_size, fps, kdf, video_button,
                 field_offset=60,
                 video_import_cb=None, slider_change_cb=None):
        self.recording_fps = fps
        self.tab_button = video_button
        self.kdf = kdf
        self.caller = caller
        self.height, self.width = height, width
        self.event_history = []
        self.root = root
        self.reviewing = False
        self.video_loaded = False
        self.video_file = None
        self.editing = False

        self.video_label = Label(self.root, bg='white')
        self.video_height, self.video_width = int((width - 10) * (1080 / 1920)), width - 10
        self.video_label.place(x=width / 2, y=5, width=self.video_width, height=self.video_height, anchor=N)

        self.load_video_button = Button(self.root, text="Load Video", font=field_font, command=video_import_cb)
        self.load_video_button.place(x=(width / 2) - 10, y=5 + (self.video_height / 2), height=button_size[1],
                                     width=button_size[0], anchor=E)

        self.camera_str_var = StringVar()
        self.audio_str_var = StringVar()
        self.recorder = None
        self.player = None
        self.deleted_event = None
        self.load_camera_box = Combobox(self.root, textvariable=self.camera_str_var, font=field_font)
        self.load_camera_box['state'] = 'readonly'
        self.load_camera_box.config(font=field_font)
        self.load_camera_box.place(x=(width / 2) + 10, y=5 + (self.video_height / 2), height=button_size[1],
                                   width=button_size[0] * 2, anchor=W)

        self.load_audio_box = Combobox(self.root, textvariable=self.audio_str_var, font=field_font)
        self.load_audio_box['state'] = 'readonly'
        self.load_camera_box.config(font=field_font)
        self.load_audio_box.place(x=(width / 2) + 10, y=50 + (self.video_height / 2), height=button_size[1],
                                  width=button_size[0] * 2, anchor=W)

        self.frame_var = IntVar(self.root)
        slider_style = self.__create_slider_style()
        self.video_slider = TickScale(self.root, orient=HORIZONTAL, variable=self.frame_var, command=slider_change_cb,
                                      style=slider_style)
        self.video_slider.config(length=self.video_width)
        self.video_slider.place(x=5, y=self.video_height + 5, anchor=NW)
        self.video_slider.config(state='disabled')
        # Event treeview shows all events in relation to the video
        event_header_dict = {"#0": ["Event Time", 'w', 1, YES, 'w']}
        event_column_dict = {"1": ["Event Tag", 'w', 1, YES, 'w'],
                             "2": ["Event Frame", 'w', 1, YES, 'w']}
        self.event_treeview_parents = []
        self.event_treeview, self.event_fs = build_treeview(self.root,
                                                            x=20, y=self.video_height + 45,
                                                            height=self.height - self.video_height - 20,
                                                            width=width - 25,
                                                            heading_dict=event_header_dict,
                                                            column_dict=event_column_dict,
                                                            button_1_bind=self.select_event,
                                                            double_bind=self.edit_event)
        # Must be pushed to a thread otherwise the session timer thread will crash
        load_cam_thread = threading.Thread(target=self.load_sources_thread)
        load_cam_thread.daemon = 1
        load_cam_thread.start()

    def __create_slider_style(self):
        """
        Creates the style for the slider
        :return: string: Name of style
        """
        try:
            fig_color = '#%02x%02x%02x' % (240, 240, 237)
            self.style = ttk.Style(self.root)
            self.style.theme_use('clam')
            # create custom layout
            self.style.layout('custom.Horizontal.TScale',
                              [('Horizontal.Scale.trough',
                                {'sticky': 'nswe',
                                 'children': [('custom.Horizontal.Scale.slider',
                                               {'side': 'left', 'sticky': ''})]})])
            self.style.configure('custom.Horizontal.TScale', background=fig_color)
        except _tkinter.TclError:
            print("INFO: Style already exists!")
            return 'custom.Horizontal.TScale'
        return 'custom.Horizontal.TScale'

    def edit_event(self, event):
        selection = self.event_treeview.identify_row(event.y)
        if selection:
            selected_event = self.event_history[int(selection)]
            EditEventPopup(self.root, self, self.kdf.dur_bindings, self.kdf.bindings, selected_event, selection)

    def popup_return(self, selection, new_value):
        if selection:
            self.event_history[int(selection)] = new_value
            self.populate_event_treeview_review()
            self.caller.pdf.save_updated_session(self.event_history)

    def load_sources_thread(self):
        try:
            self.get_camera_sources()
            self.get_audio_sources()
        except RuntimeError:
            pass

    def get_audio_sources(self):
        self.audio_source = None
        self.audio_sources = VideoRecorder.get_audio_sources()
        self.selectable_audio_sources = []
        for source in self.audio_sources:
            self.selectable_audio_sources.append(source[1])
        if not self.audio_sources:
            self.audio_str_var.set("No Microphones Found")
        else:
            self.audio_str_var.set("Select Microphone")
        self.load_audio_box['values'] = self.selectable_audio_sources
        self.load_audio_box.bind("<<ComboboxSelected>>", self.check_load_camera)

    def get_camera_sources(self):
        self.video_source = None
        self.camera_sources = VideoRecorder.get_video_sources()
        self.selectable_sources = []
        for source in self.camera_sources:
            self.selectable_sources.append(f"Input {str(source[0])}")
        if not self.camera_sources:
            self.camera_str_var.set("No Cameras Found")
        else:
            self.camera_str_var.set("Select Camera")
        self.load_camera_box['values'] = self.selectable_sources
        self.load_camera_box.bind("<<ComboboxSelected>>", self.check_load_camera)

    def check_load_camera(self, event):
        try:
            self.video_source = self.camera_sources[self.selectable_sources.index(self.camera_str_var.get())]
            self.audio_source = self.audio_sources[self.selectable_audio_sources.index(self.audio_str_var.get())]
            if self.video_source and self.audio_source:
                self.load_camera()
        except ValueError:
            return

    def select_event(self, event):
        selection = self.event_treeview.identify_row(event.y)
        if selection:
            selected_event = self.event_history[int(selection) - 1]
            if self.player:
                # Only select event when paused
                if not self.player.playing:
                    if not self.reviewing:
                        self.player.load_frame(int(selected_event[0]))

    def delete_last_event(self):
        if self.event_history:
            self.event_treeview.delete(self.event_treeview_parents[len(self.event_history) - 1])
            self.event_treeview_parents.pop(len(self.event_history) - 1)
            self.deleted_event = self.event_history[-1]
            self.event_history.pop(len(self.event_history) - 1)

    def undo_last_delete(self):
        if self.deleted_event:
            self.add_event_direct(self.deleted_event)
            self.deleted_event = None

    def add_event_direct(self, event):
        if self.video_loaded:
            self.event_history.append(event)
            self.event_treeview_parents.append(self.event_treeview.insert("", 'end', str(len(self.event_history)),
                                                                          text=str(self.event_history[-1][2]),
                                                                          values=(self.event_history[-1][1],
                                                                                  self.event_history[-1][0]),
                                                                          tags=(
                                                                              treeview_tags[
                                                                                  len(self.event_history) % 2])))
            self.event_treeview.see(self.event_treeview_parents[-1])

    def add_event(self, events):
        if self.video_loaded:
            for event in events:
                if self.editing:
                    if type(event[1]) is list and type(self.deleted_event[1]) is list:
                        event = event[:1] + self.deleted_event[1:]
                if type(event[1]) is list:
                    start_time = int(event[1][1]) - int(event[1][0])
                else:
                    start_time = event[1]
                current_frame = event[2]
                self.event_history.append((current_frame, event[0], start_time))
                self.event_treeview_parents.append(self.event_treeview.insert("", 'end', str(len(self.event_history)),
                                                                              text=str(self.event_history[-1][2]),
                                                                              values=(self.event_history[-1][1],
                                                                                      self.event_history[-1][0]),
                                                                              tags=(
                                                                                  treeview_tags[
                                                                                      len(self.event_history) % 2])))
            self.editing = False
            self.deleted_event = None
            self.event_treeview.see(self.event_treeview_parents[-1])

    def add_event_history(self, event_history):
        self.event_history = event_history

    def populate_event_treeview(self):
        if self.event_history:
            for i in range(0, len(self.event_history)):
                bind = self.event_history[i]
                self.event_treeview_parents.append(self.event_treeview.insert("", 'end', str(i), text=str(bind[2]),
                                                                              values=(bind[1], bind[0]),
                                                                              tags=(treeview_bind_tags[i % 2])))

    def clear_event_treeview(self):
        clear_treeview(self.event_treeview)
        self.event_treeview_parents = []
        self.event_history = []

    def populate_event_treeview_review(self):
        self.reviewing = True
        if self.event_history:
            for i in range(0, len(self.event_history)):
                bind = self.event_history[i]
                self.event_treeview_parents.append(self.event_treeview.insert("", 'end', str(i), text=str(bind[1]),
                                                                              values=(bind[0], bind[2]),
                                                                              tags=(treeview_bind_tags[i % 2])))

    def focus_on_event(self, index):
        select_focus(self.event_treeview, self.event_treeview_parents[index])
        scroll_to(self.event_treeview, index)

    def load_camera(self):
        if self.video_source and self.audio_source:
            if not self.recorder:
                try:
                    self.load_video_button.place_forget()
                    self.load_camera_box.place_forget()
                    self.load_audio_box.place_forget()
                    self.recorder = VideoRecorder(video_source=self.video_source,
                                                  audio_source=self.audio_source,
                                                  video_path=None,
                                                  audio_path=None,
                                                  fps=self.recording_fps,
                                                  label=self.video_label,
                                                  size=(self.video_width, self.video_height),
                                                  keep_ratio=True)
                    self.video_loaded = True
                    self.recorder.start_playback()
                    self.tab_button['text'] = 'Video View' + checkmark
                except Exception as e:
                    messagebox.showerror("Error", f"Error loading camera:\n{str(e)}")
                    print(f"ERROR: Error loading camera:\n{str(e)}\n" + traceback.print_exc())
                    self.tab_button['text'] = 'Video View' + crossmark

    def set_clip(self, start_frame, end_frame):
        if self.player:
            if start_frame < 0:
                end_frame += abs(start_frame)
                start_frame = 0
            if end_frame > self.player.nframes - 1:
                start_frame -= end_frame - self.player.nframes
                end_frame = self.player.nframes
            if not self.player.playing:
                self.player.set_clip(start_frame, end_frame)
            else:
                messagebox.showwarning("Warning", "Pause video first to set a clip!")
                print("WARNING: Pause video first to set a clip")

    def clear_clip(self):
        if self.player:
            if not self.player.playing:
                self.player.clear_clip()
            else:
                messagebox.showwarning("Warning", "Pause video first to clear a clip!")
                print("WARNING: Pause video first to clear a clip")

    def increment_frame(self):
        if self.player:
            if not self.player.playing:
                self.player.load_frame(self.player.current_frame + 1)

    def decrement_frame(self):
        if self.player:
            if not self.player.playing:
                self.player.load_frame(self.player.current_frame - 1)

    def double_speed_on(self):
        if self.player:
            self.player.frame_duration = float(1 / (self.player.fps * 2))
            return True
        return False

    def double_speed_off(self):
        if self.player:
            self.player.frame_duration = float(1 / self.player.fps)
            return True
        return False

    def load_video(self, ask=True, video_filepath=None):
        if not video_filepath and self.video_file:
            video_file = self.video_file
        else:
            if ask:
                video_file = filedialog.askopenfilename(filetypes=(("Videos", "*.mp4"),))
            else:
                video_file = video_filepath
        audio_file = os.path.join(pathlib.Path(video_file).parent, pathlib.Path(video_file).stem + ".wav")
        try:
            if video_file:
                if pathlib.Path(video_file).suffix == ".mp4":
                    self.load_video_button.place_forget()
                    self.load_camera_box.place_forget()
                    self.load_audio_box.place_forget()
                    self.video_file = video_file
                    if type(self.player) is VideoPlayer:
                        self.player.setup_streams(video_file, audio_file, self.video_label,
                                                  size=(self.video_width, self.video_height),
                                                  keep_ratio=True,
                                                  slider=None,
                                                  slider_var=self.frame_var,
                                                  override_slider=True,
                                                  cleanup_audio=True,
                                                  loading_gif='images/loading.gif')
                    else:
                        self.player = VideoPlayer(self.root, video_file, audio_file, self.video_label,
                                                  size=(self.video_width, self.video_height),
                                                  keep_ratio=True,
                                                  slider=self.video_slider,
                                                  slider_var=self.frame_var,
                                                  override_slider=True,
                                                  cleanup_audio=True,
                                                  loading_gif='images/loading.gif')
                        self.video_slider.config(state='active')
                        print(
                            f"INFO: ({self.video_width}, {self.video_height}) {self.player.size} {self.player.aspect_ratio}")
                    self.video_loaded = True
                    self.tab_button['text'] = 'Video View' + checkmark
        except Exception as e:
            messagebox.showerror("Error", f"Error loading video:\n{str(e)}")
            print(f"ERROR: Error loading video:\n{str(e)}\n" + traceback.print_exc())
            self.tab_button['text'] = 'Video View' + crossmark

    def pause_video(self):
        try:
            if self.recorder:
                self.recorder.stop_recording()
                return self.recorder.recording
            elif self.player:
                self.player.pause_video()
                return self.player.playing
            return False
        except Exception as e:
            print(f"ERROR: Error starting video:\n{str(e)}\n{traceback.print_exc()}")
            self.tab_button['text'] = 'Video View' + crossmark

    def play_video(self, video_output=None, audio_output=None):
        try:
            if self.recorder:
                self.recorder.start_recording(video_output=video_output, audio_output=audio_output)
                self.video_file = self.recorder.video_output
                self.audio_file = self.recorder.audio_output
                return self.recorder.recording
            elif self.player:
                self.player.play_video()
                return self.player.playing
            return False
        except Exception as e:
            print(f"ERROR: Error starting video:\n{str(e)}\n{traceback.print_exc()}")
            self.tab_button['text'] = 'Video View' + crossmark

    def toggle_video(self):
        try:
            if self.video_file:
                if self.player:
                    self.player.toggle_video()
                    return self.player.playing
            return False
        except Exception as e:
            print(f"ERROR: Error starting video:\n{str(e)}\n{traceback.print_exc()}")
            self.tab_button['text'] = 'Video View' + crossmark


class ViewE4:
    def __init__(self, root, height, width, field_font, header_font, button_size, e4_button, field_offset=60):
        self.root = root
        self.tab_button = e4_button
        self.session_started = False
        self.height, self.width = height, width

        self.emp_client = None
        self.e4_client = None
        self.e4_address = None
        fs_offset = 10 + ((width * 0.25) * 0.5)
        connection_offset = width * 0.15
        start_y = 25
        empatica_label = Label(self.root, text="E4 Connection", font=header_font)
        empatica_label.place(x=connection_offset, y=start_y, anchor=CENTER)

        self.empatica_button = Button(self.root, text="Start Server", command=self.start_e4_server, font=field_font)
        self.empatica_button.place(x=connection_offset, y=start_y + (field_offset / 2),
                                   width=button_size[0], height=button_size[1], anchor=CENTER)

        e4_heading_dict = {"#0": ["Visible E4s", 'c', 1, YES, 'c']}
        self.e4_treeview, self.e4_filescroll = build_treeview(self.root,
                                                              x=connection_offset,
                                                              y=start_y + field_offset,
                                                              height=height * 0.5, width=width * 0.25,
                                                              heading_dict=e4_heading_dict, anchor=N,
                                                              fs_offset=fs_offset,
                                                              button_1_bind=self.get_selection)

        self.tree_parents = []
        self.tags = ['odd', 'even']
        self.current_selection = "I000"

        self.connect_button = Button(self.root, text="Connect",
                                     command=self.connect_to_e4, width=12, font=field_font)
        self.connect_button.place(x=connection_offset, y=start_y + field_offset + height * 0.5,
                                  width=(width * 0.25) * 0.5, height=button_size[1], anchor=NE)

        self.streaming_button = Button(self.root, text="Stream",
                                       command=self.start_e4_streaming, width=12, font=field_font)
        self.streaming_button.place(x=connection_offset, y=start_y + field_offset + height * 0.5,
                                    width=(width * 0.25) * 0.5, height=button_size[1], anchor=NW)

        self.disconnected_image = PhotoImage(file='images/disconnected.png')
        self.connected_image = PhotoImage(file='images/connected.png')
        self.connected_label = Label(self.root, image=self.disconnected_image)
        self.connected_label.place(x=connection_offset - ((width * 0.25) * 0.5) * 0.5,
                                   y=(start_y + field_offset + height * 0.5) + button_size[1], anchor=N)

        self.streaming_image = PhotoImage(file='images/streaming.png')
        self.nostreaming_image = PhotoImage(file='images/nostreaming.png')
        self.streaming_label = Label(self.root, image=self.nostreaming_image)
        self.streaming_label.place(x=connection_offset + ((width * 0.25) * 0.5) * 0.5,
                                   y=(start_y + field_offset + height * 0.5) + button_size[1], anchor=N)

        self.error_thread = None
        self.devices_thread = None

        SMALL_SIZE = 8
        MEDIUM_SIZE = 10
        BIGGER_SIZE = 12

        plt.rc('font', size=SMALL_SIZE)  # controls default text sizes
        plt.rc('axes', titlesize=SMALL_SIZE)  # fontsize of the axes title
        plt.rc('axes', labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
        plt.rc('xtick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
        plt.rc('ytick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
        plt.rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
        plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

        fig_color = '#%02x%02x%02x' % (240, 240, 237)

        fig_offset = width * 0.25
        fig_width = width - fig_offset
        fig_height = (height - 70) / 3
        ani_update = 500
        # TODO: Refactor variable names
        self.hr_canvas = Canvas(self.root, width=40, height=40, bg=fig_color, bd=-2)
        self.hr_canvas.place(x=fig_offset + (fig_width * 0.2), y=start_y)
        self.hr_image = PhotoImage(file='images/heartrate.png')
        self.hr_canvas.create_image(0, 0, anchor=NW, image=self.hr_image)

        self.hr_label = Label(self.root, text="N/A", font=field_font)
        self.hr_label.place(x=fig_offset + (fig_width * 0.2) + 50, y=start_y + 10, anchor=NW)

        self.temp_canvas = Canvas(self.root, width=40, height=40, bg=fig_color, bd=-2)
        self.temp_canvas.place(x=fig_offset + (fig_width * 0.4), y=start_y)
        self.temp_image = PhotoImage(file='images/thermometer.png')
        self.temp_canvas.create_image(0, 0, anchor=NW, image=self.temp_image)

        self.temp_label = Label(self.root, text="N/A", font=field_font)
        self.temp_label.place(x=fig_offset + (fig_width * 0.4) + 50, y=start_y + 10, anchor=NW)

        self.wrist_canvas = Canvas(self.root, width=40, height=40, bg=fig_color, bd=-2)
        self.wrist_canvas.place(x=fig_offset + (fig_width * 0.6), y=start_y, anchor=NW)
        self.on_wrist_image = PhotoImage(file='images/onwrist.png')
        self.off_wrist_image = PhotoImage(file='images/offwrist.png')
        self.wrist_container = self.wrist_canvas.create_image(20, 20, anchor=CENTER, image=self.off_wrist_image)
        self.wrist = False

        self.wrist_label = Label(self.root, text="Off", font=field_font)
        self.wrist_label.place(x=fig_offset + (fig_width * 0.6) + 50, y=start_y + 10, anchor=NW)

        self.bat_image_100 = PhotoImage(file='images/battery100.png')
        self.bat_image_75 = PhotoImage(file='images/battery75.png')
        self.bat_image_50 = PhotoImage(file='images/battery50.png')
        self.bat_image_25 = PhotoImage(file='images/battery25.png')
        self.bat_canvas = Canvas(self.root, width=40, height=40, bg=fig_color, bd=-2)
        self.bat_canvas.place(x=fig_offset + (fig_width * 0.8), y=start_y)
        self.bat_container = self.bat_canvas.create_image(20, 20, anchor=CENTER, image=self.bat_image_100)

        self.bat_label = Label(self.root, text="N/A", font=field_font)
        self.bat_label.place(x=fig_offset + (fig_width * 0.8) + 50, y=start_y + 10, anchor=NW)

        dpi = 100
        px = 1 / plt.rcParams['figure.dpi']
        self.fig = Figure(figsize=(fig_width * px, fig_height * px), dpi=dpi)
        self.fig.patch.set_facecolor(fig_color)
        self.acc_plt = self.fig.add_subplot(111)
        plt.gcf().subplots_adjust(bottom=0.15)
        self.acc_plt.set_title("Accelerometer Readings")
        self.acc_plt.legend(loc="upper left")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        # self.canvas.draw()
        self.ani = animation.FuncAnimation(self.fig, self.acc_animate, fargs=([]), interval=ani_update)
        self.canvas.get_tk_widget().place(x=fig_offset + 30, y=70, anchor=NW)

        self.fig1 = Figure(figsize=(fig_width * px, fig_height * px), dpi=dpi)
        self.fig1.patch.set_facecolor(fig_color)
        self.bvp_plt = self.fig1.add_subplot(111)
        plt.gcf().subplots_adjust(bottom=0.15)
        self.bvp_plt.set_title("BVP Readings")
        self.bvp_plt.legend(loc="upper left")
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.root)  # A tk.DrawingArea.
        # self.canvas1.draw()
        self.ani1 = animation.FuncAnimation(self.fig1, self.bvp_animate, fargs=([]), interval=ani_update)
        self.canvas1.get_tk_widget().place(x=fig_offset + 30, y=70 + fig_height, anchor=NW)

        self.fig2 = Figure(figsize=(fig_width * px, fig_height * px), dpi=dpi)
        self.fig2.patch.set_facecolor(fig_color)
        self.gsr_plt = self.fig2.add_subplot(111)
        plt.gcf().subplots_adjust(bottom=0.15)
        self.gsr_plt.set_title("GSR Readings")
        self.gsr_plt.legend(loc="upper left")
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.root)  # A tk.DrawingArea.
        # self.canvas2.draw()
        self.ani2 = animation.FuncAnimation(self.fig2, self.gsr_animate, fargs=([]), interval=ani_update)
        self.canvas2.get_tk_widget().place(x=fig_offset + 30, y=70 + (fig_height * 2), anchor=NW)

        self.save_reading = False
        self.streaming = False
        self.kill = False
        self.e4 = None
        self.bat = 100
        self.windowed_readings = []
        self.update_thread = threading.Thread(target=self.update_labels_thread)

    def check_e4_error(self):
        while self.e4_client:
            if self.e4_client.client.last_error:
                messagebox.showerror("E4 Error", "Encountered error from E4!\n" + self.e4_client.client.last_error)
                print("ERROR: Encountered error from E4!\n" + self.e4_client.client.last_error)
                self.connect_to_e4()
            time.sleep(0.5)

    def disconnect_e4(self):
        if self.emp_client:
            self.emp_client.close()
        if self.e4_client:
            if self.e4_client.connected:
                self.e4_client.close()
                self.e4_client = None

    def connect_to_e4(self):
        if self.emp_client:
            try:
                if self.e4_client:
                    self.e4_client.disconnect()
                    self.connect_button.config(text="Connect")
                    self.empatica_button.config(text="Start Server")
                    self.connected_label.config(image=self.disconnected_image)
                    self.streaming_label.config(image=self.nostreaming_image)
                    self.e4_client = None
                    self.emp_client = None
                    self.tab_button['text'] = "E4 Streams" + crossmark
                else:
                    try:
                        self.e4_client = EmpaticaE4(self.e4_address)
                        if self.e4_client.connected:
                            if self.error_thread is None:
                                self.error_thread = threading.Thread(target=self.check_e4_error)
                                self.error_thread.start()
                            for stream in EmpaticaDataStreams.ALL_STREAMS:
                                self.e4_client.subscribe_to_stream(stream)
                            self.connected_label.config(image=self.connected_image)
                            self.connect_button.config(text="Disconnect")
                    except EmpaticaServerConnectError as e:
                        messagebox.showerror("Error", "Could not connect to the Empatica E4!")
                        print("ERROR: Could not connect to the Empatica E4\n" + str(e))
            except Exception as e:
                messagebox.showerror("Exception Encountered", "Encountered an error when connecting to E4:\n" + str(e))
                print("ERROR: Encountered an error when connecting to E4:\n" + traceback.print_exc())
        else:
            messagebox.showwarning("Warning", "Connect to server first!")
            print("WARNING: Connect to server first")

    def start_e4_streaming(self):
        if self.emp_client:
            if self.e4_client:
                if self.e4_client.connected:
                    try:
                        self.e4_client.start_streaming()
                        self.start_plot(self.e4_client)
                        self.streaming_label.config(image=self.streaming_image)
                        self.tab_button['text'] = "E4 Streams" + checkmark
                    except Exception as e:
                        messagebox.showerror("Exception Encountered",
                                             "Encountered an error when connecting to E4:\n" + str(e))
                        print("ERROR: Encountered error when connecting to E4:\n" + traceback.print_exc())
                else:
                    messagebox.showwarning("Warning", "Device is not connected!")
                    print("WARNING: Device is not connected")
            else:
                messagebox.showwarning("Warning", "Connect to device first!")
                print("WARNING: Connect to device first")
        else:
            messagebox.showwarning("Warning", "Connect to server first!")
            print("WARNING: Connect to server first")

    def start_e4_server(self):
        if not self.emp_client:
            try:
                self.emp_client = EmpaticaClient()
                self.empatica_button['text'] = "List Devices"
            except Exception as e:
                messagebox.showerror("Exception Encountered", "Encountered an error when connecting to E4:\n" + str(e))
                print("ERROR: Encountered an error when connecting to E4:\n" + traceback.print_exc())
        else:
            try:
                self.devices_thread = threading.Thread(target=self.list_devices_thread)
                self.devices_thread.start()
            except Exception as e:
                messagebox.showerror("Exception Encountered", "Encountered an error when connecting to E4:\n" + str(e))
                print("ERROR: Encountered an error when connecting to E4:\n" + traceback.print_exc())

    def list_devices_thread(self):
        self.emp_client.list_connected_devices()
        time.sleep(1)
        clear_treeview(self.e4_treeview)
        self.e4_treeview_parents = []
        self.populate_device_list()

    def populate_device_list(self):
        for i in range(0, len(self.emp_client.device_list)):
            self.e4_treeview_parents.append(
                self.e4_treeview.insert("", 'end', str(i),
                                        text=str(self.emp_client.device_list[i].decode("utf-8"), ),
                                        tags=(treeview_tags[i % 2])))

    def get_selection(self, event):
        selection = self.e4_treeview.identify_row(event.y)
        if selection:
            if self.emp_client:
                if len(self.emp_client.device_list) != 0:
                    self.e4_address = self.emp_client.device_list[int(selection)]
                else:
                    messagebox.showerror("Error", "No connected E4s!")
                    print("ERROR: No connected E4s")
            else:
                messagebox.showwarning("Warning", "Connect to server first!")
                print("WARNING: Connect to server first")

    def save_session(self, filename):
        if self.e4_client:
            if self.e4_client.connected:
                self.e4_client.save_readings(filename)

    def start_session(self):
        self.session_started = True
        if self.e4:
            self.e4.clear_readings()

    def stop_plot(self):
        self.streaming = False
        self.kill = True

    def start_plot(self, e4):
        self.e4 = e4
        self.windowed_readings = self.e4.windowed_readings
        if not self.streaming:
            self.streaming = True
            self.update_thread.start()

    def update_labels_thread(self):
        while self.streaming:
            if self.streaming:
                if self.e4:
                    if self.e4.connected:
                        if self.wrist != self.e4.on_wrist:
                            if self.e4.on_wrist:
                                self.wrist_canvas.delete(self.wrist_container)
                                self.wrist_container = self.wrist_canvas.create_image(20, 20, anchor=CENTER,
                                                                                      image=self.on_wrist_image)
                                self.wrist_label['text'] = "On"
                            else:
                                self.wrist_canvas.delete(self.wrist_container)
                                self.wrist_container = self.wrist_canvas.create_image(20, 20, anchor=CENTER,
                                                                                      image=self.off_wrist_image)
                                self.wrist_label['text'] = "Off"
                            self.wrist = self.e4.on_wrist
                        if len(self.e4.tmp) > 0:
                            self.temp_label['text'] = str(int(self.e4.tmp[-1])) + u"\u00b0"
                        if len(self.e4.hr) > 0:
                            self.hr_label['text'] = str(int(self.e4.hr[-1])) + " BPM"
                        if len(self.e4.bat) > 0:
                            bat = int(float(self.e4.bat[-1]) * 100.0)
                            if bat != self.bat:
                                self.bat = bat
                                if 50 < self.bat < 75:
                                    self.bat_canvas.delete(self.bat_container)
                                    self.bat_container = self.bat_canvas.create_image(20, 20, anchor=CENTER,
                                                                                      image=self.bat_image_75)
                                elif 25 < self.bat < 50:
                                    self.bat_canvas.delete(self.bat_container)
                                    self.bat_container = self.bat_canvas.create_image(20, 20, anchor=CENTER,
                                                                                      image=self.bat_image_50)
                                elif self.bat < 25:
                                    self.bat_canvas.delete(self.bat_container)
                                    self.bat_container = self.bat_canvas.create_image(20, 20, anchor=CENTER,
                                                                                      image=self.bat_image_25)
                                self.bat_label['text'] = str(self.bat) + "%"
            time.sleep(0.5)

    def acc_animate(self, e4):
        if self.streaming:
            if self.e4:
                if self.e4.connected:
                    if self.root.winfo_viewable():
                        # Limit x and y lists to 20 items
                        x_ys = self.e4.acc_x[-100:]
                        y_ys = self.e4.acc_y[-100:]
                        z_ys = self.e4.acc_z[-100:]
                        xs = np.arange(0, len(self.e4.acc_x))
                        xs = xs[-100:]

                        # Draw x and y lists
                        self.acc_plt.clear()
                        self.acc_plt.plot(xs, x_ys, label="x-axis")
                        self.acc_plt.plot(xs, y_ys, label="y-axis")
                        self.acc_plt.plot(xs, z_ys, label="z-axis")

                        # Format plot
                        plt.gcf().subplots_adjust(bottom=0.15)
                        self.acc_plt.set_title("Accelerometer Readings")
                        self.acc_plt.legend(loc="upper left")

    def bvp_animate(self, e4):
        if self.streaming:
            if self.e4:
                if self.e4.connected:
                    if self.root.winfo_viewable():
                        xs = np.arange(0, len(self.e4.bvp))
                        xs = xs[-100:]
                        x_ys = self.e4.bvp[-100:]

                        self.bvp_plt.clear()
                        self.bvp_plt.plot(xs, x_ys, label="bvp")

                        # Format plot
                        plt.gcf().subplots_adjust(bottom=0.15)
                        self.bvp_plt.set_title("BVP Readings")
                        self.bvp_plt.legend(loc="upper left")

    def gsr_animate(self, e4):
        if self.streaming:
            if self.e4:
                if self.e4.connected:
                    if self.root.winfo_viewable():
                        xs = np.arange(0, len(self.e4.gsr))
                        xs = xs[-100:]
                        x_ys = self.e4.gsr[-100:]

                        self.gsr_plt.clear()
                        self.gsr_plt.plot(xs, x_ys, label="gsr")
                        # Format plot
                        plt.gcf().subplots_adjust(bottom=0.15)
                        self.gsr_plt.set_title("GSR Readings")
                        self.gsr_plt.legend(loc="upper left")


class KeystrokeDataFields:
    def __init__(self, parent, keystroke_file, height, width,
                 field_font, header_font, button_size, caller):
        # TODO: Add editing of event history by double clicking event
        separation_distance = 30
        fs_offset = 10 + ((width * 0.25) * 0.5)
        t_width = width * 0.25

        start_y = 25
        t_y = start_y + 15
        th_offset = t_y * 2

        self.height, self.width = height, width
        self.frame = parent
        self.caller = caller

        keystroke_label = Label(self.frame, text="Frequency Bindings", font=header_font)
        keystroke_label.place(x=(width * 0.25) - 30, y=start_y, anchor=CENTER)
        freq_heading_dict = {"#0": ["Char", 'c', 1, YES, 'c']}
        freq_column_dict = {"1": ["Freq", 'c', 1, YES, 'c'],
                            "2": ["Tag", 'c', 1, YES, 'c']}
        self.freq_treeview, self.freq_filescroll = build_treeview(self.frame,
                                                                  x=(width * 0.25) - separation_distance, y=t_y,
                                                                  height=height - th_offset, width=t_width,
                                                                  column_dict=freq_column_dict,
                                                                  heading_dict=freq_heading_dict,
                                                                  # button_1_bind=self.get_freq_selection,
                                                                  # double_bind=self.change_freq_keybind,
                                                                  anchor=N,
                                                                  tag_dict=treeview_bind_tag_dict,
                                                                  fs_offset=fs_offset)

        dur_label = Label(self.frame, text="Duration Bindings", font=header_font)
        dur_label.place(x=width * 0.5, y=start_y, anchor=CENTER)
        dur_heading_dict = {"#0": ["Char", 'c', 1, YES, 'c']}
        dur_column_dict = {"1": ["Dur", 'c', 1, YES, 'c'],
                           "2": ["Total", 'c', 1, YES, 'c'],
                           "3": ["Tag", 'c', 1, YES, 'c']}
        self.dur_treeview, self.dur_filescroll = build_treeview(self.frame,
                                                                x=width * 0.5, y=t_y,
                                                                height=height - th_offset, width=t_width,
                                                                column_dict=dur_column_dict,
                                                                heading_dict=dur_heading_dict,
                                                                # button_1_bind=self.get_dur_selection,
                                                                # double_bind=self.change_dur_keybind,
                                                                anchor=N,
                                                                tag_dict=treeview_bind_tag_dict,
                                                                fs_offset=fs_offset)

        sh_label = Label(self.frame, text="Session History", font=header_font)
        sh_label.place(x=(width * 0.75) + 30, y=start_y, anchor=CENTER)
        sh_heading_dict = {"#0": ["Event", 'c', 1, YES, 'c']}
        sh_column_dict = {"1": ["Time", 'c', 1, YES, 'c']}
        self.sh_treeview, self.sh_filescroll = build_treeview(self.frame,
                                                              x=(width * 0.75) + separation_distance, y=t_y,
                                                              height=height - th_offset, width=t_width,
                                                              column_dict=sh_column_dict,
                                                              heading_dict=sh_heading_dict,
                                                              # double_bind=self.delete_event,
                                                              anchor=N,
                                                              tag_dict=treeview_bind_tag_dict,
                                                              fs_offset=fs_offset)

        self.key_explanation = Label(self.frame, font=field_font, text="Delete Last Event: Backspace"
                                                                       "\nUndo Last Delete: Right Ctrl"
                                                                       "\nEdit Last Event: Left Shift", justify=LEFT)
        self.key_explanation.place(x=((width * 0.75) + 30) - ((width * 0.25) * 0.5),
                                   y=height - (th_offset / 2), anchor=NW)

        self.init_background_vars(keystroke_file)

    def init_background_vars(self, keystroke_file):
        # Setup variables used
        self.keystroke_json = None
        self.new_keystroke = False
        self.deleted_event = None
        self.editing = False
        self.bindings = []
        self.event_history = []
        self.dur_bindings = []
        self.bindings_freq = []
        self.key_file = keystroke_file
        self.conditions = []
        self.freq_strings = []
        self.freq_key_strings = []
        self.dur_sticky = []
        self.sticky_start = []
        self.sticky_dur = []
        self.sh_treeview_parents, self.freq_treeview_parents, self.dur_treeview_parents = [], [], []
        self.sh_c_selection, self.freq_c_selection, self.dur_c_selection = "I000", "I000", "I000"
        # Access files and populate on screen
        self.open_keystroke_file()
        self.populate_freq_bindings()
        self.populate_dur_bindings()
        self.populate_sh_bindings()

    def clear_sh_treeview(self):
        clear_treeview(self.sh_treeview)
        self.sh_treeview_parents = []
        self.event_history = []

    def add_session_event(self, events):
        for event in events:
            if self.editing:
                if type(event[1]) == type(self.deleted_event[1]):
                    event = event[:1] + self.deleted_event[1:]
            if type(event[1]) is list:
                start_time = int(event[1][1]) - int(event[1][0])
            else:
                start_time = event[1]
            self.event_history.append(event)
            self.sh_treeview_parents.append(self.sh_treeview.insert("", 'end', str(len(self.event_history)),
                                                                    text=str(self.event_history[-1][0]),
                                                                    values=(start_time,),
                                                                    tags=(treeview_tags[len(self.event_history) % 2])))
        self.editing = False
        self.deleted_event = None
        self.sh_treeview.see(self.sh_treeview_parents[-1])

    def undo_last_delete(self):
        if self.deleted_event:
            if type(self.deleted_event[1]) is list:
                self.update_dur_event(self.deleted_event[0], (self.deleted_event[1][1] - self.deleted_event[1][0]))
            else:
                self.update_freq_event(self.deleted_event[0], 1)
            self.add_session_event([self.deleted_event])
            self.deleted_event = None

    def delete_last_event(self):
        if self.event_history:
            if not self.deleted_event:
                self.sh_treeview.delete(self.sh_treeview_parents[len(self.event_history) - 1])
                self.sh_treeview_parents.pop(len(self.event_history) - 1)
                self.deleted_event = self.event_history[-1]
                self.event_history.pop(len(self.event_history) - 1)
                if type(self.deleted_event[1]) is list:
                    self.update_dur_event(self.deleted_event[0], -(self.deleted_event[1][1] - self.deleted_event[1][0]))
                else:
                    self.update_freq_event(self.deleted_event[0], -1)

    def delete_dur_binding(self):
        if self.current_selection1:
            self.dur_bindings.pop(int(self.current_selection1))
            clear_treeview(self.dur_treeview)
            self.populate_dur_bindings()

    def add_dur_popup(self):
        NewKeyPopup(self, self.frame, True)

    def update_freq_event(self, key_char, change):
        for i in range(0, len(self.bindings)):
            if self.bindings[i][1] == key_char:
                self.bindings_freq[i] += change
                self.freq_treeview.set(str(i), column="1", value=self.bindings_freq[i])

    def update_dur_event(self, key_char, change):
        for i in range(0, len(self.dur_bindings)):
            if self.dur_bindings[i][1] == key_char:
                self.sticky_dur[i] += change
                self.sticky_start[i] = 0
                self.dur_treeview.set(str(i), column="2", value=self.sticky_dur[i])

    def check_key(self, key_char, start_time, current_frame, current_window, current_audio_frame):
        return_bindings = []
        for i in range(0, len(self.bindings)):
            if self.bindings[i][0] == key_char:
                self.bindings_freq[i] += 1
                self.freq_treeview.set(str(i), column="1", value=self.bindings_freq[i])
                return_bindings.append((self.bindings[i][1], start_time, current_frame,
                                        current_window, current_audio_frame))
        for i in range(0, len(self.dur_bindings)):
            if self.dur_bindings[i][0] == key_char:
                if self.dur_sticky[i]:
                    self.dur_treeview.item(str(i), tags=treeview_bind_tags[i % 2])
                    self.caller.pdf.hide_dur_key(i)
                    self.dur_sticky[i] = False
                    duration = [self.sticky_start[i][0], start_time]
                    frame = [self.sticky_start[i][1], current_frame]
                    window = [self.sticky_start[i][2], current_window]
                    audio = [self.sticky_start[i][3], current_audio_frame]
                    return_bindings.append((self.dur_bindings[i][1], duration, frame,
                                            window, audio))
                    self.sticky_dur[i] += start_time - self.sticky_start[i][0]
                    self.sticky_start[i] = 0
                    self.dur_treeview.set(str(i), column="2", value=self.sticky_dur[i])
                else:
                    self.dur_treeview.item(str(i), tags=treeview_bind_tags[2])
                    self.caller.pdf.show_dur_key(i)
                    self.dur_sticky[i] = True
                    self.sticky_start[i] = (start_time, current_frame, current_window, current_audio_frame)
        if return_bindings:
            # Clear deleted event buffer when a new event is added but not when editing
            if not self.editing:
                if self.deleted_event:
                    self.deleted_event = None
            return return_bindings

    def add_key_popup(self):
        NewKeyPopup(self, self.frame, False)

    def get_sh_selection(self, event):
        self.current_selection2 = self.sh_treeview.identify_row(event.y)

    def get_dur_selection(self, event):
        self.current_selection1 = self.dur_treeview.identify_row(event.y)

    def get_freq_selection(self, event):
        self.current_selection = self.freq_treeview.identify_row(event.y)

    def import_binding(self):
        pass

    def save_binding(self):
        x = {
            "Name": self.keystroke_json["Name"],
            "Frequency": self.bindings,
            "Duration": self.dur_bindings
        }
        with open(self.key_file, 'w') as f:
            json.dump(x, f)

    def delete_freq_binding(self):
        if self.current_selection:
            self.bindings.pop(int(self.current_selection))
            clear_treeview(self.freq_treeview)
            self.populate_freq_bindings()

    def change_dur_keybind(self, event):
        selection = self.dur_treeview.identify_row(event.y)
        if selection:
            Popup(self, self.frame, int(selection), True)

    def change_freq_keybind(self, event):
        selection = self.freq_treeview.identify_row(event.y)
        if selection:
            Popup(self, self.frame, int(selection), False)

    def update_dur_keybind(self, tag, key):
        self.dur_bindings[key] = (self.dur_bindings[key][0], tag)
        self.dur_treeview.set(str(key), column="1", value=tag)

    def update_freq_keybind(self, tag, key):
        self.bindings[key] = (self.bindings[key][0], tag)
        self.freq_treeview.set(str(key), column="1", value=tag)

    def add_freq_keybind(self, tag, key):
        self.bindings.append((tag, key))
        self.bindings_freq.append(0)
        clear_treeview(self.freq_treeview)
        self.populate_freq_bindings()

    def add_dur_keybind(self, tag, key):
        self.dur_bindings.append((tag, key))
        clear_treeview(self.dur_treeview)
        self.populate_dur_bindings()

    def open_keystroke_file(self):
        with open(self.key_file) as f:
            self.keystroke_json = json.load(f)
        if len(self.keystroke_json) == 1:
            messagebox.showerror("Error", "Keystroke file is empty, which it should not be!")
            print(f"ERROR: Keystroke file is empty\n{self.key_file}\n{self.keystroke_json}")
        else:
            for key in self.keystroke_json:
                if key == "Frequency":
                    for binding in self.keystroke_json[key]:
                        # TODO: Refactor this variable to 'freq_bindings'
                        self.bindings.append(binding)
                        # TODO: What is this variable and why do I do this to myself
                        self.bindings_freq.append(0)
                elif key == "Duration":
                    for binding in self.keystroke_json[key]:
                        self.dur_bindings.append(binding)
                elif key == "Conditions":
                    for binding in self.keystroke_json[key]:
                        self.conditions.append(binding)

    def populate_freq_bindings(self):
        for i in range(0, len(self.bindings)):
            bind = self.bindings[i]
            self.freq_treeview_parents.append(self.freq_treeview.insert("", 'end', str(i), text=str(bind[0]),
                                                                        values=(self.bindings_freq[i], bind[1]),
                                                                        tags=(treeview_bind_tags[i % 2])))

    def populate_dur_bindings(self):
        for i in range(0, len(self.dur_bindings)):
            bind = self.dur_bindings[i]
            self.dur_sticky.append(False)
            self.sticky_start.append(0)
            self.sticky_dur.append(0)
            self.dur_treeview_parents.append(self.dur_treeview.insert("", 'end', str(i), text=str(bind[0]),
                                                                      values=(0, 0, bind[1]),
                                                                      tags=(treeview_bind_tags[i % 2])))

    def populate_sh_bindings(self):
        if self.event_history:
            for i in range(0, len(self.event_history)):
                bind = self.event_history[i]
                self.sh_treeview_parents.append(self.sh_treeview.insert("", 'end', str(i), text=str(bind[0]),
                                                                        values=(bind[1],),
                                                                        tags=(treeview_bind_tags[i % 2])))


class NewKeyPopup:
    def __init__(self, top, root, dur_freq):
        self.caller = top
        self.dur_freq = dur_freq
        self.tag_entry = None
        self.key_entry = None
        self.popup_root = None
        self.patient_name_entry_pop_up(root)

    def patient_name_entry_pop_up(self, root):
        # Create a Toplevel window
        popup_root = self.popup_root = Toplevel(root)
        popup_root.config(bg="white", bd=-2)
        popup_root.geometry("300x100")
        popup_root.title("Enter New Binding")

        # Create an Entry Widget in the Toplevel window
        self.tag_label = Label(popup_root, text="Key Tag", bg='white')
        self.tag_label.place(x=30, y=20, anchor=W)
        self.tag_entry = Entry(popup_root, bd=2, width=25, bg='white')
        self.tag_entry.place(x=90, y=20, anchor=W)

        self.key_label = Label(popup_root, text="Key", bg='white')
        self.key_label.place(x=30, y=50, anchor=W)
        self.key_entry = Entry(popup_root, bd=2, width=25, bg='white')
        self.key_entry.place(x=90, y=50, anchor=W)

        # Create a Button Widget in the Toplevel Window
        button = Button(popup_root, text="OK", command=self.close_win)
        button.place(x=150, y=70, anchor=N)

    def close_win(self):
        if len(self.key_entry.get()) == 1:
            if not self.dur_freq:
                self.caller.add_keybind(self.tag_entry.get(), self.key_entry.get())
            else:
                self.caller.add_durbind(self.tag_entry.get(), self.key_entry.get())
            self.popup_root.destroy()


class Popup:
    def __init__(self, top, root, tag, dur_key):
        self.caller = top
        self.dur_key = dur_key
        self.entry = None
        self.popup_root = None
        self.tag = tag
        self.patient_name_entry_pop_up(root)

    def patient_name_entry_pop_up(self, root):
        # Create a Toplevel window
        popup_root = self.popup_root = Toplevel(root)
        popup_root.config(bg="white", bd=-2)
        popup_root.geometry("300x50")
        popup_root.title("Enter New Key Bind")

        # Create an Entry Widget in the Toplevel window
        self.entry = Entry(popup_root, bd=2, width=25)
        self.entry.pack()

        # Create a Button Widget in the Toplevel Window
        button = Button(popup_root, text="OK", command=self.close_win)
        button.pack(pady=5, side=TOP)

    def close_win(self):
        if len(self.entry.get()) == 1:
            if not self.dur_key:
                self.caller.update_keybind(self.entry.get(), self.tag)
            else:
                self.caller.update_durbind(self.entry.get(), self.tag)
            self.popup_root.destroy()
