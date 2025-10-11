"""
    Custom combo box widget that more closely implements an 'autocomplete' box that people are used to
"""

import sys
import tkinter as tk
from tkinter import ttk
from pprint import pprint

class AutoComplete(ttk.Combobox):

    #  TODO: ttk.Combobox isn't skinnable in EDMC
    # So... can we create our own widget with an entry box and listbox ?
    # Test theme on individual components first
    # Otherwise, stick with combobox, but use it on the settings sheet only

    def __init__(self, master: tk.Frame, textvariable: tk.StringVar, values: list, **kwargs):     
        style = ttk.Style()
        style.configure("TCombobox", fieldbackground="green3")
        
        super().__init__(master, textvariable=textvariable, values=values, **kwargs)
        

        # Based on https://mail.python.org/pipermail/tkinter-discuss/2012-January/003041.html
        self._initialOptions = values
        self._filtered_options = sorted(values, key=str.lower)
        self._hits = [textvariable.get()]
        self._hit_index = 0

        self.bind('<KeyRelease>', self._filter_options)
        self.bind('<FocusOut>', self._loose_focus)
        self.bind('<FocusIn>', self._gain_focus)
        self.bind('<<ComboboxSelected>>', self._item_selected)


    def _filter_options(self, event):
        if event.keysym == 'BackSpace':
            self.delete(self.index(tk.INSERT), tk.END)

        # If a new character has been entered, then filter the results
        if len(event.char) == 1:
            self._autocomplete()

    def _autocomplete(self, event=None):
        size = len(self.get())

        hits = []
        if size == 0:
            hits == self._initialOptions
        else:
            for option in self._initialOptions:
                if option.lower().startswith(self.get().lower()):
                    hits.append(option)

        if hits != self._hits:
            self._hit_index = 0
            self._hits = hits
            if hits:
                self['values'] = hits
            else:
                self['values'] = self._initialOptions
        
        if self._hits and hits == self._hits:
            self._hit_index = self._hit_index % len(self._hits)

        if self._hits:
            self.delete(0, tk.END)
            self.insert(0, self._hits[self._hit_index])
            self.select_range(size, tk.END)

    def _loose_focus(self, event=None):
        if not self._hits:
            self.set('')
        self['values'] = self._initialOptions

    def _gain_focus(self, event=None):
        self.select_range(0, tk.END)

    def _item_selected(self, event=None):
        self._autocomplete(event)
        self.select_clear()
        self['values'] = self._initialOptions