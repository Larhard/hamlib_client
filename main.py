#!/usr/bin/env python

import tkinter as tk
from tkinter import ttk

import json
import datetime
import time

from threading import Thread
from queue import Queue

import Hamlib

import ham_alert_client
import config


class HamAlertClientGUI:
    def __init__(self):
        self._window = tk.Tk()
        self._window.title("HamAlert Client")

        self._alerts_table = ttk.Treeview(self._window, columns=("time", "callsign", "frequency", "mode", "source", "reference", "qth"), show="headings", selectmode="browse")

        self._alerts_table.heading("time", text="QTU")
        self._alerts_table.column("time", width=120, stretch=False)
        self._alerts_table.heading("callsign", text="QRA")
        self._alerts_table.column("callsign", width=100, stretch=False)
        self._alerts_table.heading("frequency", text="QRG")
        self._alerts_table.column("frequency", width=80, stretch=False, anchor="e")
        self._alerts_table.heading("mode", text="Mode")
        self._alerts_table.column("mode", width=80, stretch=False)
        self._alerts_table.heading("source", text="Src")
        self._alerts_table.column("source", width=100, stretch=False)
        self._alerts_table.heading("reference", text="Ref")
        self._alerts_table.column("reference", width=100, stretch=False)
        self._alerts_table.heading("qth", text="QTH")
        self._alerts_table.column("qth", width=100, stretch=True)

        self._alerts_table.bind("<<TreeviewSelect>>", func=self.do_select_alert)

        self._alerts_scrollbar = ttk.Scrollbar(self._window,
                orient="vertical",
                command=self._alerts_table.yview)
        self._alerts_table.configure(yscrollcommand=self._alerts_scrollbar.set)

        self._auto_scroll = tk.BooleanVar()
        self._auto_scroll_checkbox = ttk.Checkbutton(text="Auto-scroll", variable=self._auto_scroll)

        self._alerts_table.pack(side="left", fill="both", expand=True)
        self._alerts_scrollbar.pack(side="left", fill="both")
        self._auto_scroll_checkbox.pack(side="top")

        self._action_queue = Queue()
        self._action_event = "<<action>>"
        self._window.bind(self._action_event, self._process_action_queue)

        Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)

        self._rig = Hamlib.Rig(getattr(Hamlib, "RIG_MODEL_{}".format(config.RIG_MODEL)))
        self._rig.set_conf("rig_pathname", config.RIG_PATH)
        self._rig.set_conf("retry", "5")
        self._rig.set_conf("serial_speed", str(config.RIG_BAUDRATE))
        self._rig.open()

        self._first_timestamp = None
        self._last_timestamp = None
        self._timeout = None
        self._timeout_count = 0

        self._watch_alerts_thread = Thread(target=self._watch_alerts_job, daemon=True)
        self._auto_scroll_thread = Thread(target=self._auto_scroll_job, daemon=True)

    def do_select_alert(self, event):
        index, = self._alerts_table.selection()
        data = self._alerts_table.item(index)
        time, callsign, frequency, mode, *_ = data["values"]
        frequency = int(float(frequency) * 1E6)

        self._rig.set_freq(Hamlib.RIG_VFO_A, frequency)
        self._rig.set_vfo(Hamlib.RIG_VFO_A)

        if mode.upper() == "SSB":
            mode = "USB" if frequency >= 1E7 else "LSB"

        mode_id = getattr(Hamlib, "RIG_MODE_{}".format(mode.upper()))
        self._rig.set_mode(mode_id, -1)

    def _get_timestamp(self, time_str):
        time = datetime.time.fromisoformat(time_str)
        now = datetime.datetime.utcnow()

        timestamp = datetime.datetime.combine(now, time)

        while timestamp - now > datetime.timedelta(hours=12):
            timestamp -= datetime.timedelta(days=1)

        while timestamp - now < datetime.timedelta(hours=-12):
            timestamp += datetime.timedelta(days=1)

        return timestamp

    def _update_timeout(self, timestamp):
        if self._first_timestamp is None:
            self._first_timestamp = timestamp
        else:
            self._timeout = (timestamp - self._first_timestamp) / self._timeout_count

        self._timeout_count += 1
        self._last_timestamp = timestamp

    def do_add_alert(self, alert):
        time_str = alert.get("time", "Unknown")
        callsign = alert.get("fullCallsign", "Unknown")
        frequency = alert.get("frequency", "Unknown")
        mode = alert.get("mode", "Unknown")
        source = alert.get("source", "Unknown")
        qth = alert.get("entity", "Unknown")
        ref = ""

        if source == "sotawatch":
            qth += ": " + alert.get("summitName", "Unknown")
            ref = alert.get("summitRef", "Unknown")

        if source == "pota":
            qth += ": " + alert.get("wwffName", "Unknown")
            ref = alert.get("wwffRef", "Unknown")

        timestamp = self._get_timestamp(time_str)

        self._alerts_table.insert(parent="", index=0, values=(
            timestamp.strftime("%Y-%m-%d %H:%M"),
            callsign,
            frequency,
            mode,
            source,
            ref,
            qth,
        ))

        self._update_timeout(timestamp)

    def do_scroll(self):
        selection = self._alerts_table.selection()
        if not selection:
            new_selection = self._alerts_table.get_children()[0]
        else:
            new_selection = self._alerts_table.prev(selection)

        if new_selection:
            self._alerts_table.selection_set(new_selection)

    def _send_action(self, action, *args, **kwargs):
        data = {
            "action": action,
            "args": args,
            "kwargs": kwargs,
        }

        self._action_queue.put(data)
        self._window.event_generate(self._action_event, when="tail")

    def _process_action_queue(self, event):
        while not self._action_queue.empty():
            data = self._action_queue.get(block=False)
            action = getattr(self, data['action'])
            action(*data['args'], **data['kwargs'])

    def _auto_scroll_job(self):
        while True:
            if self._timeout is not None:
                time.sleep(self._timeout.total_seconds() * 0.9)
            else:
                time.sleep(1)

            if self._auto_scroll.get():
                self._send_action("do_scroll")

    def _watch_alerts_job(self):
        with ham_alert_client.Client(config.USERNAME, config.PASSWORD, sources_filter=config.SOURCES_FILTER) as client:
            for alert in client:
                self._send_action("do_add_alert", alert=alert)

    def start(self):
        self._watch_alerts_thread.start()
        self._auto_scroll_thread.start()

        self._window.mainloop()

def main():
    gui = HamAlertClientGUI()
    gui.start()


if __name__ == "__main__":
    main()
