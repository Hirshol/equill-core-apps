# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.
from ew.util import ew_logging
from sdk.widgets.selectable_list import SelectableList
from sdk.widgets.label import Label
from ew.internal_decs.wifi_item import WifiItem


logger = ew_logging.getLogger('ew.internal_decs.scan_wifi_overlay')

class ScanWifiDialog(SelectableList):

    def __init__(self, w, h, parent_window=None):
        self.title = "Available Networks"
        SelectableList.__init__(self, w, h, parent_window=parent_window)
        self.num_rows = 10
        self.row_height = 40
        self.line_spacer = 10
        self.offset = 8
    
    def clear_net_list(self):
        logger.debug("Clearing net list")
        self.clean_widgets()
        offset = 5
        top_left = (self.box.top_left()[0]+offset, 
                self.box.top_left()[1]+offset)
        bottom_right = (self.box.bottom_right()[0]-offset,
                self.box.bottom_right()[1]-offset)
        self.clear_area(top_left, bottom_right)

    def set_scan_state(self, state):
        self.clear_net_list()
        self.add_title()
        logger.debug("Scan state: %r", state)
        state_label = Label(state, self.w, self.row_height, 16)
        self.add(state_label, self.offset*4, 
                self.title_label.y + self.title_label.h + self.row_height)
        self.update(True)

    def draw_net_list(self, available_networks):
        # Code to build network list
        logger.debug("Drawing net list")         
        count = 0
        known_list = []
        widget_items = []
        for item in available_networks:
            # TODO: Support more than 8 entries
            entries = item.split('\t')
            if count > self.num_rows - 1:
                break
            w_id = "ssid_%s" % entries[0]
            if w_id not in known_list and entries[0].strip():
                net_row = WifiItem(
                        self.w-self.offset*2, 
                        self.row_height, w_id)
                net_row.create_gui(self)
                net_row.set_from_data(entries)
                known_list.append(w_id)
                widget_items.append(net_row)
                count = count + 1
        self.load(widget_items)