#!/usr/bin/env python

import tkinter as tk
from tkinter import ttk

import json

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
        self._alerts_table.column("time", width=80, stretch=False)
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

        self._alerts_table.pack(side="left", fill="both", expand=True)
        self._alerts_scrollbar.pack(side="left", fill="both")

        self._action_queue = Queue()
        self._action_event = "<<action>>"
        self._window.bind(self._action_event, self._process_action_queue)

        Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)

        self._rig = Hamlib.Rig(getattr(Hamlib, "RIG_MODEL_{}".format(config.RIG_MODEL)))
        self._rig.set_conf("rig_pathname", config.RIG_PATH)
        self._rig.set_conf("retry", "5")
        self._rig.set_conf("serial_speed", str(config.RIG_BAUDRATE))
        self._rig.open()

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

    def do_add_alert(self, alert):
        time = alert["time"]
        callsign = alert["fullCallsign"]
        frequency = alert["frequency"]
        mode = alert["mode"]
        source = alert["source"]
        qth = alert["entity"]
        ref = ""

        if source == "sotawatch":
            qth += ": " + alert["summitName"]
            ref = alert["summitRef"]

        if source == "pota":
            qth += ": " + alert["wwffName"]
            ref = alert["wwffRef"]

        self._alerts_table.insert(parent="", index=0, values=(
            time,
            callsign,
            frequency,
            mode,
            source,
            ref,
            qth,
        ))


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

    def _watch_alerts(self):
        with ham_alert_client.Client(config.USERNAME, config.PASSWORD) as client:
            for alert in client:
                self._send_action("do_add_alert", alert=alert)

    def start(self):
        watch_alerts_thread = Thread(target=self._watch_alerts, daemon=True)
        watch_alerts_thread.start()

        self._window.mainloop()

def main():
    gui = HamAlertClientGUI()
    gui.start()


if __name__ == "__main__":
    main()
