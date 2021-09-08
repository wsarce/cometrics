import os
import pathlib
import time
from os import walk
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Treeview, Style
import json
import datetime
from PIL import Image, ImageTk
import threading
from pynput import keyboard
import winsound
# Custom library imports
from pyempatica.empaticae4 import EmpaticaClient, EmpaticaE4, EmpaticaDataStreams
from logger_util import *
from output_view_ui import OutputViewPanel


class KeystrokeDataFields:
    def __init__(self, parent, keystroke_file):
        self.frame = Frame(parent, width=250, height=(parent.winfo_screenheight() - 280))
        self.frame.place(x=520, y=120)
        self.keystroke_json = None
        self.new_keystroke = False
        self.bindings = []
        self.bindings_freq = []
        self.key_file = keystroke_file
        self.open_keystroke_file()

        keystroke_label = Label(self.frame, text="Key Bindings", font=('Purisa', 12))
        keystroke_label.place(x=125, y=15, anchor=CENTER)

        style = Style()
        style.configure("mystyle.Treeview", highlightthickness=0, bd=0,
                        font=('Calibri', 10))  # Modify the font of the body
        style.configure("mystyle.Treeview.Heading", font=('Calibri', 13, 'bold'))  # Modify the font of the headings
        style.map('Treeview', foreground=self.fixed_map('foreground'),
                  background=self.fixed_map('background'))
        # style.layout("mystyle.Treeview", [('mystyle.Treeview.treearea', {'sticky': 'nswe'})])  # Remove the borders
        self.treeview = Treeview(self.frame, style="mystyle.Treeview", height=18, selectmode='browse')
        self.treeview.place(x=20, y=30, height=(parent.winfo_screenheight() - 350), width=210)

        self.treeview.heading("#0", text="Char", anchor='c')
        self.treeview["columns"] = ["1", "2"]
        self.treeview.column("#0", width=40, stretch=NO, anchor='c')
        self.treeview.heading("1", text="Freq")
        self.treeview.column("1", width=40, stretch=NO, anchor='c')
        self.treeview.heading("2", text="Tag")
        self.treeview.column("2", width=65, stretch=YES, anchor='c')

        self.treeview.tag_configure('odd', background='#E8E8E8')
        self.treeview.tag_configure('even', background='#DFDFDF')
        self.treeview.tag_configure('toggle', background='red')

        self.treeview.bind("<Button-1>", self.get_selection)
        self.treeview.bind("<Double-Button-1>", self.change_keybind)

        self.file_scroll = Scrollbar(self.frame, orient="vertical", command=self.treeview.yview)
        self.file_scroll.place(x=2, y=30, height=(parent.winfo_screenheight() - 350))

        self.treeview.configure(yscrollcommand=self.file_scroll.set)
        self.tree_parents = []
        self.tags = ['odd', 'even', 'toggle']
        self.current_selection = "I000"

        self.populate_bindings()

        self.delete_button = Button(self.frame, text="Delete Key", command=self.delete_binding, width=8)
        self.delete_button.place(x=20, y=parent.winfo_screenheight() - 320)

        self.add_button = Button(self.frame, text="Add Key", command=self.add_key_popup, width=9)
        self.add_button.place(x=125, y=parent.winfo_screenheight() - 320, anchor=N)

        self.save_button = Button(self.frame, text="Save File", command=self.save_binding, width=8)
        self.save_button.place(x=230, y=parent.winfo_screenheight() - 320, anchor=NE)

    def check_key(self, key_char):
        return_bindings = []
        for i in range(0, len(self.bindings)):
            if self.bindings[i][1] == key_char:
                self.bindings_freq[i] += 1
                return_bindings.append(self.bindings[i][0])
        if return_bindings:
            self.clear_listbox()
            self.populate_bindings()
            return return_bindings

    def add_key_popup(self):
        NewKeyPopup(self, self.frame)

    def get_selection(self, event):
        self.current_selection = self.treeview.identify_row(event.y)

    def save_binding(self):
        x = {"Name": self.keystroke_json["Name"]}
        for binding in self.bindings:
            x.update({str(binding[0]): str(binding[1])})
        with open(self.key_file, 'w') as f:
            json.dump(x, f)

    def delete_binding(self):
        if self.current_selection:
            self.bindings.pop(int(self.current_selection))
            self.clear_listbox()
            self.populate_bindings()

    def fixed_map(self, option):
        # https://stackoverflow.com/a/62011081
        # Fix for setting text colour for Tkinter 8.6.9
        # From: https://core.tcl.tk/tk/info/509cafafae
        #
        # Returns the style map for 'option' with any styles starting with
        # ('!disabled', '!selected', ...) filtered out.

        # style.map() returns an empty list for missing options, so this
        # should be future-safe.
        style = Style()
        return [elm for elm in style.map('Treeview', query_opt=option) if
                elm[:2] != ('!disabled', '!selected')]

    def change_keybind(self, event):
        selection = self.treeview.identify_row(event.y)
        if selection:
            Popup(self, self.frame, int(selection))

    def update_keybind(self, tag, key):
        self.bindings[key] = (self.bindings[key][0], tag)
        self.clear_listbox()
        self.populate_bindings()

    def add_keybind(self, tag, key):
        self.bindings.append((tag, key))
        self.bindings_freq.append(0)
        self.clear_listbox()
        self.populate_bindings()

    def clear_listbox(self):
        for children in self.treeview.get_children():
            self.treeview.delete(children)

    def open_keystroke_file(self):
        with open(self.key_file) as f:
            self.keystroke_json = json.load(f)
        if len(self.keystroke_json) == 1:
            self.new_keystroke = True
        else:
            for key in self.keystroke_json:
                if key != "Name":
                    self.bindings.append((key, self.keystroke_json[key]))
                    self.bindings_freq.append(0)

    def populate_bindings(self, sticky=None):
        for i in range(0, len(self.bindings)):
            if sticky:
                if sticky == i:
                    self.tree_parents.append(self.treeview.insert("", 'end', str(i), text=self.bindings[i][1],
                                                                  values=(self.bindings_freq[i], self.bindings[i][0],),
                                                                  tags=(self.tags[2])))
                    continue
            self.tree_parents.append(self.treeview.insert("", 'end', str(i), text=self.bindings[i][1],
                                                          values=(self.bindings_freq[i], self.bindings[i][0],),
                                                          tags=(self.tags[i % 2])))


class NewKeyPopup:
    def __init__(self, top, root):
        self.caller = top
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
            self.caller.add_keybind(self.tag_entry.get(), self.key_entry.get())
            self.popup_root.destroy()


class Popup:
    def __init__(self, top, root, tag):
        self.caller = top
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
            self.caller.update_keybind(self.entry.get(), self.tag)
            self.popup_root.destroy()


class EmpaticaDataFields:
    def __init__(self, parent, output_view):
        self.ovu = output_view
        self.parent = parent
        self.frame = Frame(parent, width=250, height=(parent.winfo_screenheight() - 280))
        self.frame.place(x=265, y=120)

        self.emp_client = None
        self.e4_client = None
        self.e4_address = None

        empatica_label = Label(self.frame, text="Empatica E4", font=('Purisa', 12))
        empatica_label.place(x=125, y=15, anchor=CENTER)

        self.empatica_button = Button(self.frame, text="Start Server", command=self.start_e4_server)
        self.empatica_button.place(x=125, y=30, anchor=N)

        style = Style()
        style.configure("mystyle.Treeview", highlightthickness=0, bd=0,
                        font=('Calibri', 10))  # Modify the font of the body
        style.configure("mystyle.Treeview.Heading", font=('Calibri', 13, 'bold'))  # Modify the font of the headings
        style.map('Treeview', foreground=self.fixed_map('foreground'),
                  background=self.fixed_map('background'))
        # style.layout("mystyle.Treeview", [('mystyle.Treeview.treearea', {'sticky': 'nswe'})])  # Remove the borders
        self.treeview = Treeview(self.frame, style="mystyle.Treeview", height=18, selectmode='browse')
        self.treeview.place(x=20, y=65, height=(parent.winfo_screenheight() - 450), width=210)

        self.treeview.heading("#0", text="#", anchor='c')
        self.treeview["columns"] = ["1"]
        self.treeview.column("#0", width=65, stretch=NO, anchor='c')
        self.treeview.heading("1", text="E4 Name")
        self.treeview.column("1", width=65, stretch=YES, anchor='c')

        self.treeview.tag_configure('odd', background='#E8E8E8')
        self.treeview.tag_configure('even', background='#DFDFDF')
        self.treeview.bind("<Button-1>", self.get_selection)

        self.file_scroll = Scrollbar(self.frame, orient="vertical", command=self.treeview.yview)
        self.file_scroll.place(x=2, y=65, height=(parent.winfo_screenheight() - 450))

        self.treeview.configure(yscrollcommand=self.file_scroll.set)
        self.tree_parents = []
        self.tags = ['odd', 'even']
        self.current_selection = "I000"

        self.connect_button = Button(self.frame, text="Connect", command=self.connect_to_e4, width=12)
        self.connect_button.place(x=20, y=(parent.winfo_screenheight() - 385))

        self.streaming_button = Button(self.frame, text="Stream", command=self.start_e4_streaming, width=12)
        self.streaming_button.place(x=230, y=(parent.winfo_screenheight() - 385), anchor=NE)

        self.connected_label = Label(self.frame, text="CONNECTED", fg='green')
        self.streaming_label = Label(self.frame, text="STREAMING", fg='green')

        self.devices_thread = None

    def disconnect_e4(self):
        if self.emp_client:
            self.emp_client.close()
        if self.e4_client:
            if self.e4_client.connected:
                self.e4_client.close()

    def connect_to_e4(self):
        if self.emp_client:
            try:
                self.e4_client = EmpaticaE4(self.e4_address)
                if self.e4_client.connected:
                    for stream in EmpaticaDataStreams.ALL_STREAMS:
                        self.e4_client.subscribe_to_stream(stream)
                    self.connected_label.place(x=125, y=(self.parent.winfo_screenheight() - 350), anchor=N)
            except Exception as e:
                messagebox.showerror("Exception Encountered", "Encountered an error when connecting to E4:\n" + str(e))
        else:
            messagebox.showwarning("Warning", "Connect to server first!")

    def start_e4_streaming(self):
        if self.emp_client:
            if self.e4_client:
                if self.e4_client.connected:
                    try:
                        self.e4_client.start_streaming()
                        self.ovu.e4_view.start_plot(self.e4_client)
                        self.streaming_label.place(x=125, y=(self.parent.winfo_screenheight() - 320), anchor=N)
                    except Exception as e:
                        messagebox.showerror("Exception Encountered",
                                             "Encountered an error when connecting to E4:\n" + str(e))
                else:
                    messagebox.showwarning("Warning", "Device is not connected!")
            else:
                messagebox.showwarning("Warning", "Connect to device first!")
        else:
            messagebox.showwarning("Warning", "Connect to server first!")

    def start_e4_server(self):
        if not self.emp_client:
            try:
                self.emp_client = EmpaticaClient()
                self.empatica_button['text'] = "List Devices"
            except Exception as e:
                messagebox.showerror("Exception Encountered", "Encountered an error when connecting to E4:\n" + str(e))
        else:
            try:
                self.devices_thread = threading.Thread(target=self.list_devices_thread)
                self.devices_thread.start()
            except Exception as e:
                messagebox.showerror("Exception Encountered", "Encountered an error when connecting to E4:\n" + str(e))

    def list_devices_thread(self):
        self.emp_client.list_connected_devices()
        time.sleep(1)
        self.clear_device_list()
        self.populate_device_list()

    def clear_device_list(self):
        for children in self.treeview.get_children():
            self.treeview.delete(children)

    def populate_device_list(self):
        for i in range(0, len(self.emp_client.device_list)):
            self.tree_parents.append(self.treeview.insert("", 'end', str(i), text=str(i),
                                                          values=(self.emp_client.device_list[i].decode("utf-8"),),
                                                          tags=(self.tags[i % 2])))

    def get_selection(self, event):
        self.current_selection = self.treeview.identify_row(event.y)
        if self.current_selection:
            if self.emp_client:
                if len(self.emp_client.device_list) != 0:
                    self.e4_address = self.emp_client.device_list[int(self.current_selection)]
                else:
                    messagebox.showerror("Error", "No connected E4s!")
            else:
                messagebox.showwarning("Warning", "Connect to server first!")

    def save_session(self, filename):
        if self.e4_client:
            if self.e4_client.connected:
                self.e4_client.save_readings(filename)

    def fixed_map(self, option):
        # https://stackoverflow.com/a/62011081
        # Fix for setting text colour for Tkinter 8.6.9
        # From: https://core.tcl.tk/tk/info/509cafafae
        #
        # Returns the style map for 'option' with any styles starting with
        # ('!disabled', '!selected', ...) filtered out.

        # style.map() returns an empty list for missing options, so this
        # should be future-safe.
        style = Style()
        return [elm for elm in style.map('Treeview', query_opt=option) if
                elm[:2] != ('!disabled', '!selected')]