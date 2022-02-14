import json
import math
from tkinter import *
from tkinter.ttk import Combobox

from ksf_utils import open_keystroke_file
from tkinter_utils import build_treeview
from ui_params import treeview_bind_tags


class PatientDataVar:
    PATIENT_NAME = 0
    MRN = 1
    SESS_LOC = 2
    ASSESS_NAME = 3
    COND_NAME = 4
    PRIM_THER = 5
    CASE_MGR = 6
    SESS_THER = 7
    DATA_REC = 8
    SESS_NUM = 9
    PRIM_DATA = 10


class PatientDataFields:
    def __init__(self, parent, x, y, height, width, patient_file, prim_session_number, reli_session_number,
                 session_date, session_time, conditions, ksf, field_offset=50,
                 header_font=('Purisa', 14), field_font=('Purisa', 12), debug=False):
        self.x, self.y = x, y
        self.conditions = conditions
        self.patient = PatientContainer(patient_file)
        self.prim_session_num, self.reli_session_num = prim_session_number, reli_session_number

        field_count = int(height / field_offset)
        if field_count < 13:
            field_count = int((height * 0.85) / field_offset)
        frame_count = int(math.ceil(13 / field_count)) + 1
        self.patient_frames = []
        self.next_button_image = PhotoImage(file='images/go_next.png')
        self.prev_button_image = PhotoImage(file='images/go_previous.png')
        print(f"INFO: Number of fields: {field_count}")
        for i in range(0, frame_count):
            self.patient_frames.append(Frame(parent, width=width, height=height))
            patient_information = Label(self.patient_frames[-1], text="Patient Information", font=header_font)
            patient_information.place(x=width / 2, y=15, anchor=CENTER)
            if frame_count > 1:
                next_button = Button(self.patient_frames[-1], image=self.next_button_image,
                                     command=self.next_patient_field)
                prev_button = Button(self.patient_frames[-1], image=self.prev_button_image,
                                     command=self.prev_patient_field)
                next_button.place(x=width - 15, y=height * 0.9, anchor=E)
                prev_button.place(x=15, y=height * 0.9, anchor=W)
                page_text = Label(self.patient_frames[-1], text=f"{i + 1}/{frame_count}", font=header_font)
                page_text.place(x=width / 2, y=height * 0.9, anchor=CENTER)
        print(f"INFO: Number of frames: {frame_count}")
        self.patient_vars = [
            StringVar(self.patient_frames[math.ceil(1 / field_count) - 1]),
            StringVar(self.patient_frames[math.ceil(2 / field_count) - 1]),
            StringVar(self.patient_frames[math.ceil(3 / field_count) - 1]),
            StringVar(self.patient_frames[math.ceil(4 / field_count) - 1]),
            StringVar(self.patient_frames[math.ceil(5 / field_count) - 1]),
            StringVar(self.patient_frames[math.ceil(6 / field_count) - 1]),
            StringVar(self.patient_frames[math.ceil(7 / field_count) - 1]),
            StringVar(self.patient_frames[math.ceil(8 / field_count) - 1]),
            StringVar(self.patient_frames[math.ceil(9 / field_count) - 1]),
            StringVar(self.patient_frames[math.ceil(10 / field_count) - 1], value=prim_session_number),
            StringVar(self.patient_frames[math.ceil(11 / field_count) - 1], value="Primary")
        ]
        self.label_texts = [
            "Name",
            "Medical Record Number",
            "Session Location",
            "Assessment Name",
            "Condition Name",
            "Primary Therapist",
            "Case Manager",
            "Session Therapist",
            "Data Recorder",
            "Session Number",
            "Primary or Reliability Session"
        ]
        if self.patient.name:
            self.patient_vars[PatientDataVar.PATIENT_NAME].set(self.patient.name)
            self.patient_name = self.patient.name
        if self.patient.medical_record_number:
            self.patient_vars[PatientDataVar.MRN].set(self.patient.medical_record_number)
        self.session_number = prim_session_number
        self.patient_entries, self.patient_labels = [], []

        patient_dict = [
            [Label, self.label_texts[PatientDataVar.PATIENT_NAME], self.patient_vars[PatientDataVar.PATIENT_NAME]],
            [Entry, self.label_texts[PatientDataVar.PATIENT_NAME], self.patient_vars[PatientDataVar.PATIENT_NAME]],
            [Label, self.label_texts[PatientDataVar.MRN], self.patient_vars[PatientDataVar.MRN]],
            [Entry, self.label_texts[PatientDataVar.MRN], self.patient_vars[PatientDataVar.MRN]],
            [Label, self.label_texts[PatientDataVar.SESS_LOC], self.patient_vars[PatientDataVar.SESS_LOC]],
            [Entry, self.label_texts[PatientDataVar.SESS_LOC], self.patient_vars[PatientDataVar.SESS_LOC]],
            [Label, self.label_texts[PatientDataVar.ASSESS_NAME], self.patient_vars[PatientDataVar.ASSESS_NAME]],
            [Entry, self.label_texts[PatientDataVar.ASSESS_NAME], self.patient_vars[PatientDataVar.ASSESS_NAME]],
            [Label, self.label_texts[PatientDataVar.COND_NAME], self.patient_vars[PatientDataVar.COND_NAME]],
            [Combobox, self.label_texts[PatientDataVar.COND_NAME], self.patient_vars[PatientDataVar.COND_NAME]],
            [Label, self.label_texts[PatientDataVar.PRIM_THER], self.patient_vars[PatientDataVar.PRIM_THER]],
            [Entry, self.label_texts[PatientDataVar.PRIM_THER], self.patient_vars[PatientDataVar.PRIM_THER]],
            [Label, self.label_texts[PatientDataVar.CASE_MGR], self.patient_vars[PatientDataVar.CASE_MGR]],
            [Entry, self.label_texts[PatientDataVar.CASE_MGR], self.patient_vars[PatientDataVar.CASE_MGR]],
            [Label, self.label_texts[PatientDataVar.SESS_THER], self.patient_vars[PatientDataVar.SESS_THER]],
            [Entry, self.label_texts[PatientDataVar.SESS_THER], self.patient_vars[PatientDataVar.SESS_THER]],
            [Label, self.label_texts[PatientDataVar.DATA_REC], self.patient_vars[PatientDataVar.DATA_REC]],
            [Entry, self.label_texts[PatientDataVar.DATA_REC], self.patient_vars[PatientDataVar.DATA_REC]],
            [Label, self.label_texts[PatientDataVar.SESS_NUM], self.patient_vars[PatientDataVar.SESS_NUM]],
            [Entry, self.label_texts[PatientDataVar.SESS_NUM], self.patient_vars[PatientDataVar.SESS_NUM]],
        ]
        # TODO: Create key viewer on a page appended at the end of the other pages
        info_count = 0
        frame_select = 0
        patient_y = 30
        for elem in range(0, len(patient_dict), 2):
            temp_label = patient_dict[elem][0](self.patient_frames[frame_select], text=patient_dict[elem][1],
                                               font=field_font)
            self.patient_labels.append(temp_label)
            temp_label.place(x=5, y=patient_y, anchor=NW)
            if patient_dict[elem + 1][0] is Combobox:
                temp_entry = patient_dict[elem + 1][0](self.patient_frames[frame_select],
                                                       textvariable=patient_dict[elem][2], font=field_font)
                temp_entry['values'] = self.conditions
                temp_entry['state'] = 'readonly'
                temp_entry.config(font=field_font)
                temp_entry.place(x=15, y=patient_y + (field_offset / 2), anchor=NW, width=width * 0.88)
                self.patient_frames[frame_select].option_add('*TCombobox*Listbox.font', field_font)
            else:
                temp_entry = patient_dict[elem + 1][0](self.patient_frames[frame_select], font=field_font,
                                                       textvariable=patient_dict[elem][2])
                temp_entry.place(x=15, y=patient_y + (field_offset / 2), anchor=NW, width=width * 0.88)
            self.patient_entries.append(temp_entry)
            info_count += 1
            if not info_count % field_count and frame_count != 1:
                frame_select += 1
                patient_y = 30
            else:
                if patient_dict[elem + 1][0] is OptionMenu:
                    patient_y += field_offset
                else:
                    patient_y += field_offset

        primary_data = Label(self.patient_frames[frame_select], text=self.label_texts[PatientDataVar.PRIM_DATA],
                             font=field_font)
        primary_data.place(x=5, y=patient_y, anchor=NW)
        prim_data_radio = Radiobutton(self.patient_frames[frame_select], text="Primary", value="Primary",
                                      variable=self.patient_vars[PatientDataVar.PRIM_DATA], command=self.check_radio,
                                      font=field_font, width=12)
        rel_data_radio = Radiobutton(self.patient_frames[frame_select], text="Reliability", value="Reliability",
                                     variable=self.patient_vars[PatientDataVar.PRIM_DATA], command=self.check_radio,
                                     font=field_font, width=12)
        prim_data_radio.place(x=(width / 2), y=patient_y + (field_offset / 2), anchor=NE)
        rel_data_radio.place(x=(width / 2), y=patient_y + (field_offset / 2), anchor=NW)
        self.patient_entries.append(prim_data_radio)
        self.patient_entries.append(rel_data_radio)
        info_count += 1
        if not info_count % field_count and frame_count != 1:
            frame_select += 1
            patient_y = 30
        else:
            patient_y += field_offset
        # Session date field
        date_label = Label(self.patient_frames[frame_select], text="Session Date: " + session_date, anchor=NW,
                           font=field_font)
        date_label.place(x=5, y=patient_y, anchor=NW)
        info_count += 1
        info_count += 1
        if not info_count % field_count and frame_count != 1:
            frame_select += 1
            patient_y = 30
        else:
            patient_y += field_offset / 2
        # Session start time field
        self.start_label = Label(self.patient_frames[frame_select], text="Session Start Time: " + session_time,
                                 anchor=NW, font=field_font)
        self.start_label.place(x=5, y=patient_y, anchor=NW)

        self.patient_vars[PatientDataVar.PATIENT_NAME].set(self.patient.name)
        if self.patient.medical_record_number:
            self.patient_vars[PatientDataVar.MRN].set(self.patient.medical_record_number)
        self.patient_vars[PatientDataVar.SESS_NUM].set(prim_session_number)

        self.current_patient_field = 0
        self.patient_frames[self.current_patient_field].place(x=self.x, y=self.y)
        self.patient_entries[0].focus()

        self.freq_bindings, self.dur_bindings, _ = open_keystroke_file(ksf)
        self.bindings = []
        self.bindings.extend(self.freq_bindings)
        self.bindings.extend(self.dur_bindings)

        dur_heading_dict = {"#0": ["Char", 'c', 50, NO, 'c']}
        dur_column_dict = {"1": ["Tag", 'c', 1, YES, 'c']}
        self.bind_treeview, self.bind_filescroll = build_treeview(self.patient_frames[-1],
                                                                  x=width / 2, y=30,
                                                                  height=height * 0.8, width=width - 30,
                                                                  column_dict=dur_column_dict,
                                                                  heading_dict=dur_heading_dict,
                                                                  anchor=N,
                                                                  fs_offset=(width / 2) - 7)
        for i in range(0, len(self.bindings)):
            bind = self.bindings[i]
            self.bind_treeview.insert("", 'end', str(i), text=str(bind[0]),
                                      values=(bind[1],),
                                      tags=(treeview_bind_tags[i % 2]))
        if debug:
            self.patient_vars[PatientDataVar.SESS_LOC].set("Debug")
            self.patient_vars[PatientDataVar.ASSESS_NAME].set("Debug")
            self.patient_vars[PatientDataVar.COND_NAME].set("Debug")
            self.patient_vars[PatientDataVar.CASE_MGR].set("Debug")
            self.patient_vars[PatientDataVar.SESS_THER].set("Debug")
            self.patient_vars[PatientDataVar.DATA_REC].set("Debug")
            self.patient_vars[PatientDataVar.PRIM_THER].set("Debug")

    def select_patient_fields(self, field):
        self.patient_frames[self.current_patient_field].place_forget()
        self.patient_frames[field].place(x=self.x, y=self.y)
        self.current_patient_field = field

    def next_patient_field(self):
        self.patient_frames[self.current_patient_field].place_forget()
        if self.current_patient_field + 1 >= len(self.patient_frames):
            self.current_patient_field = 0
        else:
            self.current_patient_field += 1
        self.patient_frames[self.current_patient_field].place(x=self.x, y=self.y)

    def prev_patient_field(self):
        self.patient_frames[self.current_patient_field].place_forget()
        if self.current_patient_field - 1 < 0:
            self.current_patient_field = len(self.patient_frames) - 1
        else:
            self.current_patient_field -= 1
        self.patient_frames[self.current_patient_field].place(x=self.x, y=self.y)

    def check_radio(self):
        if self.patient_vars[PatientDataVar.PRIM_DATA].get() == "Primary":
            self.patient_vars[PatientDataVar.SESS_NUM].set(self.prim_session_num)
            self.session_number = self.prim_session_num
        elif self.patient_vars[PatientDataVar.PRIM_DATA].get() == "Reliability":
            self.patient_vars[PatientDataVar.SESS_NUM].set(self.reli_session_num)
            self.session_number = self.reli_session_num
        else:
            print(f"ERROR: Something went wrong assigning the session type "
                  f"{self.patient_vars[PatientDataVar.PRIM_DATA].get()}")

    def save_patient_fields(self):
        self.patient.save_patient(self.patient_vars[PatientDataVar.PATIENT_NAME].get(),
                                  self.patient_vars[PatientDataVar.MRN].get())

    def check_session_fields(self):
        if self.patient_vars[PatientDataVar.SESS_LOC].get() == "":
            return "Session location not set!"
        elif self.patient_vars[PatientDataVar.ASSESS_NAME].get() == "":
            return "Assessment name not set!"
        elif self.patient_vars[PatientDataVar.COND_NAME].get() == "":
            return "Condition name not set!"
        elif self.patient_vars[PatientDataVar.PRIM_THER].get() == "":
            return "Primary therapist name not set!"
        elif self.patient_vars[PatientDataVar.CASE_MGR].get() == "":
            return "Case manager name not set!"
        elif self.patient_vars[PatientDataVar.SESS_THER].get() == "":
            return "Session therapist name not set!"
        elif self.patient_vars[PatientDataVar.DATA_REC].get() == "":
            return "Data recorder not set!"
        elif self.patient_vars[PatientDataVar.PRIM_DATA].get() == "":
            return "Data type not set!"
        elif int(self.patient_vars[PatientDataVar.SESS_NUM].get()) < self.session_number and self.patient_vars[
            PatientDataVar.PRIM_DATA].get() == "Primary":
            return "Session number already exists!"
        else:
            return False

    def lock_session_fields(self):
        for entry in self.patient_entries:
            entry.config(state='disabled')
        self.patient_frames[self.current_patient_field].place_forget()
        self.current_patient_field = len(self.patient_frames) - 1
        self.patient_frames[-1].place(x=self.x, y=self.y)

    def get_session_fields(self):
        return {"Session Location": self.patient_vars[PatientDataVar.SESS_LOC].get(),
                "Assessment Name": self.patient_vars[PatientDataVar.ASSESS_NAME].get(),
                "Condition Name": self.patient_vars[PatientDataVar.COND_NAME].get(),
                "Primary Therapist": self.patient_vars[PatientDataVar.PRIM_THER].get(),
                "Case Manager": self.patient_vars[PatientDataVar.CASE_MGR].get(),
                "Session Therapist": self.patient_vars[PatientDataVar.SESS_THER].get(),
                "Data Recorder": self.patient_vars[PatientDataVar.DATA_REC].get(),
                "Primary Data": self.patient_vars[PatientDataVar.PRIM_DATA].get(),
                "Session Number": self.patient_vars[PatientDataVar.SESS_NUM].get()
                }


class PatientContainer:
    def __init__(self, patient_file):
        self.source_file = patient_file
        self.patient_json = None
        self.patient_path = None
        self.name = None
        self.medical_record_number = None
        if patient_file:
            self.update_fields(patient_file)

    def update_fields(self, filepath):
        f = open(filepath)
        self.patient_json = json.load(f)
        self.name = self.patient_json["Name"]
        self.medical_record_number = self.patient_json["MRN"]

    def save_patient(self, name, mrn):
        with open(self.source_file, 'w') as f:
            x = {
                "Name": name,
                "MRN": mrn
            }
            json.dump(x, f)
