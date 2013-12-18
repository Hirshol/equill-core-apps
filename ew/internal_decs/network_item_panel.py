#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
from sdk.widgets.panel import Panel
from sdk.widgets.image_label import ImageLabel
from sdk.widgets.image_status import ImageStatus
from sdk.widgets.label import Label
from ew.util import ew_logging


logger = ew_logging.getLogger('ew.internal_decs.settings_class')

class NetworkItemPanel(Panel):

    type_responds_to_strokes = True

    def __init__(self, width, height, widget_id=None):
        Panel.__init__(self, width, height, (), widget_id)
        self.start_x = 4
        self.start_y = 4
        self.spacer = 4
        self.open_network = True
        self.known = False
        self.connected = False

    def responds_to_strokes(self):
        return self.type_responds_to_strokes

    def on_stroke(self, index, last, eraser, button, current_stroke,
            save_data=None):
        if last:
            current_stroke.set_consumed()
            self.notify_listeners("on_select", self)

    def create_gui(self, network_page):
        self.name  = Label('', 700, 30, 16)
        #self.type  = Label('', 200, 30, 16)
        self.check = ImageLabel('current_net', 24, 24, path="sets/settings/check.pgm")
        self.wifi_lock = ImageLabel('wifi_lock', 24, 24, path="sets/settings/wifi_lock.pgm")
        self.circle = ImageLabel('known_net', 10, 10, path="sets/settings/circle.pgm")
        wifi_dict = {63: 'sets/settings/wifi0.pgm', 126: 'sets/settings/wifi1.pgm',
                189: 'sets/settings/wifi2.pgm', 255: 'sets/settings/wifi3.pgm'}
        self.wifi = ImageStatus('wifi_strength', 24, 24, wifi_dict, 63)
        self.add(self.name, self.start_x + self.check.w + self.spacer, self.start_y)
        #self.add(self.type, self.name.x+self.name.w+10, self.start_y)
        self.add(self.wifi, self.w - 50, self.start_y)

    def set_from_data(self, net):
        connected = net[-1]
        if connected == "COMPLETED":
            self.add(self.check, self.start_x, 0)
            self.connected = True
        if net[5] == "yes":
            self.add(self.circle, self.wifi.x+self.wifi.w+self.circle.w, 
                    self.wifi.y+self.wifi.h/2-self.circle.h/2)
            self.known = True
        signal_level = int(net[3])
        # TODO: The math may need some tweaking
        status = [ signal_item for signal_item in [63, 126, 189, 255] \
                if signal_level % signal_item == signal_level ]
        self.wifi.set_status(status[0])
        self.name.set_text(net[0])
        supported_network = ['WPA', 'WPA2', 'WEP']
        for item in supported_network:
            if item in net[2]:
                self.open_network = False
                break
        if not self.open_network:
            self.add(self.wifi_lock, self.wifi.x-self.wifi.w/4-self.wifi_lock.w, 
                    self.wifi.y+self.wifi.h/2-self.wifi_lock.h/2)