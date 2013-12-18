#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
"""
Utilities related to the display server binary function call message protocol
"""

from ew.util import ew_binary_message
from ew_binary_message import EwBinaryMessage

class DsMessage(EwBinaryMessage):
    def __init__(self):
        EwBinaryMessage.__init__(self, option_bit_values = {
            # Listed alphabetically.
            'clear_ink':         16,
            'delete_image':       8,
            'disable_page_turn': 32,
            'flash':              2,
            'force_reload':       1,
            'redraw':             4,
        })

DsMessageError = EwBinaryMessage.Error

if __name__ == '__main__':
    ew_binary_message.test(DsMessage())
