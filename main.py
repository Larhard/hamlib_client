#!/usr/bin/env python

import tkinter as tk
from tkinter import ttk

import json

from threading import Thread
from queue import Queue

import ham_alert_client
import config


class HamAlertClientGUI:
    def __init__(self):
        self._window = tk.Tk()
        self._window.title("HamAlert Client")

        self._alerts_table = ttk.Treeview(self._window, columns=("QTU", "QRA", "QRG", "Mode", "Src", "QTH", "Ref"), show="headings")
        self._alerts_table.heading("QTU", text="QTU")
        self._alerts_table.heading("QRA", text="QRA")
        self._alerts_table.heading("QRG", text="QRG")
        self._alerts_table.heading("Mode", text="Mode")
        self._alerts_table.heading("Src", text="Src")
        self._alerts_table.heading("QTH", text="QTH")
        self._alerts_table.heading("Ref", text="Ref")
        self._alerts_table.pack()

        self._action_queue = Queue()
        self._action_event = "<<action>>"
        self._window.bind(self._action_event, self._process_action_queue)

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
            qth,
            ref,
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
