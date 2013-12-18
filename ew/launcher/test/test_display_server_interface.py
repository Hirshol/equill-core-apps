#!/usr/bin/python
# Copyright 2011 Ricoh Innovations, Inc.

import sys, os, threading, time, unittest

from ew.util import ew_logging
ew_logging.reinitialize(log_stderr=True)
import logging
# Set up environment to put the display_server module into testable mode.
# Enable the newer 32-bit interface.
os.environ['EW_DS_PARAMETERS_32_BIT'] = 'true'
import ew.launcher.display_server
from ew.launcher import display_server
# This tells the display_server module to not connect to a socket.
display_server.interface_testing = True
display_server.logger.setLevel(logging.INFO)
from ew.launcher.display_server import DisplayServer, notify_event
from ew.util.ds_message import DsMessage, DsMessageError

verbose = False

send_data = None

ds_message = DsMessage()

def _send(self, msg):
    global send_data
    send_data = data = ds_message.decode(msg)
    if verbose:
        print 'total length:', data.total_length
        print 'op code:', data.op_code
        print 'options:', '0x%08x => %s' % (
                data.options.options_int, data.options)
        print 'request id:', data.request_id
        print 'int args:', data.int_args
        print 'char args:', data.char_args


# Replace the socket send method with the above that instead of sending to
# a socket, decodes the data so that we can check it.
DisplayServer._send = _send

# Parameters for testing methods with wait=True mode.
wait_time = 0.6
min_acceptable_actual_wait_time = wait_time - 0.005
excessively_long_wait_time = wait_time + 1.0

wait_start = None

def notify_later():
    """Starts a thread to notify waiting methods after a short time."""
    global wait_start
    wait_start = time.time()
    request_id = (display_server.request_namespace |
            display_server.prev_request_number + 1)
    def helper():
        time.sleep(wait_time)
        notify_event('on_nothing', request_id)
    threading.Thread(target=helper).start()


def notify_check():
    """Checks that waiting methods waited for about the correct time,
        allowing for real-time uncertainties."""
    elapsed = time.time() - wait_start
    if elapsed >= min_acceptable_actual_wait_time:
        if elapsed >= excessively_long_wait_time:
            print ('@@@ Excessively long wait: expected time: %.3f,'
                    ' actual %.3f, excess %.3f' %
                    (wait_time, elapsed, elapsed - wait_time))
        return None
    return 'Wait error: expected time: %.3f, actual %.3f, error %.3f' % (
            wait_time, elapsed, wait_time - elapsed)


# Create a DisplayServer instance to test.
ds = DisplayServer.instance()


class TestDisplayServerInterface(unittest.TestCase):
    """
    Test each method of the ew.display_server.DisplayServer class.
    """

    # ===============================================================

    # Test set for "load_document"
    #   Parameters: start_page_num, document_path:s
    #   Options: flash, force_reload
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-loaddocument

    def test_load_document_defaults(self):
        if verbose:
            print '\nload_document defaults'

        try:
            ds.load_document(
                    1,
                    "2",
                    # flash=False,
                    # force_reload=False,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 100)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1,))
        self.assertEqual(send_data.char_args, ("2",))

    def test_load_document_nondefault(self):
        if verbose:
            print '\nload_document non-default'

        try:
            ds.load_document(
                    1,
                    "2",
                    flash=True,
                    force_reload=True,
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 100)
        self.assertEqual(send_data.options, 0x00000003)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, (1,))
        self.assertEqual(send_data.char_args, ("2",))

    def test_load_document_nondefault_w_wait(self):
        if verbose:
            print '\nload_document non-default & wait'
        notify_later()
        try:
            ds.load_document(
                    1,
                    "2",
                    flash=True,
                    force_reload=True,
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 100)
        self.assertEqual(send_data.options, 0x00000003)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1,))
        self.assertEqual(send_data.char_args, ("2",))

    def test_load_document_opcode_property(self):
        self.assertEqual(ds.load_document.opcode, 100)

    # ===============================================================

    # Test set for "insert_page"
    #   Parameters: page_id:s, insert_before:s
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-insertpage%5C

    def test_insert_page_defaults(self):
        if verbose:
            print '\ninsert_page defaults'

        try:
            ds.insert_page(
                    "1",
                    "2",
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 101)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1", "2"))

    def test_insert_page_nondefault(self):
        if verbose:
            print '\ninsert_page non-default'

        try:
            ds.insert_page(
                    "1",
                    "2",
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 101)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1", "2"))

    def test_insert_page_nondefault_w_wait(self):
        if verbose:
            print '\ninsert_page non-default & wait'
        notify_later()
        try:
            ds.insert_page(
                    "1",
                    "2",
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 101)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1", "2"))

    def test_insert_page_opcode_property(self):
        self.assertEqual(ds.insert_page.opcode, 101)

    # ===============================================================

    # Test set for "delete_page"
    #   Parameters: page_id:s
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-deletepage%5C

    def test_delete_page_defaults(self):
        if verbose:
            print '\ndelete_page defaults'

        try:
            ds.delete_page(
                    "1",
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 102)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1",))

    def test_delete_page_nondefault(self):
        if verbose:
            print '\ndelete_page non-default'

        try:
            ds.delete_page(
                    "1",
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 102)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1",))

    def test_delete_page_nondefault_w_wait(self):
        if verbose:
            print '\ndelete_page non-default & wait'
        notify_later()
        try:
            ds.delete_page(
                    "1",
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 102)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1",))

    def test_delete_page_opcode_property(self):
        self.assertEqual(ds.delete_page.opcode, 102)

    # ===============================================================

    # Test set for "update_region_of_page"
    #   Parameters: x_dest, y_dest, x_src, y_src, width_src, height_src,
    #         page_id:s, src_path:s
    #   Options: clear_ink, delete_image, flash, redraw
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-updateregionofpage

    def test_update_region_of_page_defaults(self):
        if verbose:
            print '\nupdate_region_of_page defaults'

        try:
            ds.update_region_of_page(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    "7",
                    "8",
                    # clear_ink=False,
                    # delete_image=False,
                    # flash=False,
                    # redraw=False,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 103)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ("7", "8"))

    def test_update_region_of_page_nondefault(self):
        if verbose:
            print '\nupdate_region_of_page non-default'

        try:
            ds.update_region_of_page(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    "7",
                    "8",
                    clear_ink=True,
                    delete_image=True,
                    flash=True,
                    redraw=True,
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 103)
        self.assertEqual(send_data.options, 0x0000001e)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ("7", "8"))

    def test_update_region_of_page_nondefault_w_wait(self):
        if verbose:
            print '\nupdate_region_of_page non-default & wait'
        notify_later()
        try:
            ds.update_region_of_page(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    "7",
                    "8",
                    clear_ink=True,
                    delete_image=True,
                    flash=True,
                    redraw=True,
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 103)
        self.assertEqual(send_data.options, 0x0000001e)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ("7", "8"))

    def test_update_region_of_page_opcode_property(self):
        self.assertEqual(ds.update_region_of_page.opcode, 103)

    # ===============================================================

    # Test set for "update_region_of_infobar"
    #   Parameters: x_dest, y_dest, x_src, y_src, width_src, height_src
    #   Options: clear_ink, flash, redraw
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-updateregionofinfobar%5C

    def test_update_region_of_infobar_defaults(self):
        if verbose:
            print '\nupdate_region_of_infobar defaults'

        try:
            ds.update_region_of_infobar(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    # clear_ink=False,
                    # flash=False,
                    # redraw=False,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 104)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ())

    def test_update_region_of_infobar_nondefault(self):
        if verbose:
            print '\nupdate_region_of_infobar non-default'

        try:
            ds.update_region_of_infobar(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    clear_ink=True,
                    flash=True,
                    redraw=True,
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 104)
        self.assertEqual(send_data.options, 0x00000016)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ())

    def test_update_region_of_infobar_nondefault_w_wait(self):
        if verbose:
            print '\nupdate_region_of_infobar non-default & wait'
        notify_later()
        try:
            ds.update_region_of_infobar(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    clear_ink=True,
                    flash=True,
                    redraw=True,
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 104)
        self.assertEqual(send_data.options, 0x00000016)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ())

    def test_update_region_of_infobar_opcode_property(self):
        self.assertEqual(ds.update_region_of_infobar.opcode, 104)

    # ===============================================================

    # Test set for "jump_to_page"
    #   Parameters: page_id:s
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-jumptopage

    def test_jump_to_page_defaults(self):
        if verbose:
            print '\njump_to_page defaults'

        try:
            ds.jump_to_page(
                    "1",
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 105)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1",))

    def test_jump_to_page_nondefault(self):
        if verbose:
            print '\njump_to_page non-default'

        try:
            ds.jump_to_page(
                    "1",
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 105)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1",))

    def test_jump_to_page_nondefault_w_wait(self):
        if verbose:
            print '\njump_to_page non-default & wait'
        notify_later()
        try:
            ds.jump_to_page(
                    "1",
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 105)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1",))

    def test_jump_to_page_opcode_property(self):
        self.assertEqual(ds.jump_to_page.opcode, 105)

    # ===============================================================

    # Test set for "next_page"
    #   Parameters: none
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-nextpage

    def test_next_page_defaults(self):
        if verbose:
            print '\nnext_page defaults'

        try:
            ds.next_page(
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 106)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_next_page_nondefault(self):
        if verbose:
            print '\nnext_page non-default'

        try:
            ds.next_page(
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 106)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_next_page_nondefault_w_wait(self):
        if verbose:
            print '\nnext_page non-default & wait'
        notify_later()
        try:
            ds.next_page(
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 106)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_next_page_opcode_property(self):
        self.assertEqual(ds.next_page.opcode, 106)

    # ===============================================================

    # Test set for "prev_page"
    #   Parameters: none
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-prevpage

    def test_prev_page_defaults(self):
        if verbose:
            print '\nprev_page defaults'

        try:
            ds.prev_page(
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 107)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_prev_page_nondefault(self):
        if verbose:
            print '\nprev_page non-default'

        try:
            ds.prev_page(
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 107)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_prev_page_nondefault_w_wait(self):
        if verbose:
            print '\nprev_page non-default & wait'
        notify_later()
        try:
            ds.prev_page(
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 107)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_prev_page_opcode_property(self):
        self.assertEqual(ds.prev_page.opcode, 107)

    # ===============================================================

    # Test set for "create_overlay_window"
    #   Parameters: x_dest, y_dest, x_src, y_src, width_src, height_src,
    #         page_id:s, display_window_id:s, src_path:s
    #   Options: clear_ink, delete_image, disable_page_turn, flash, redraw
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-createoverlaywindow

    def test_create_overlay_window_defaults(self):
        if verbose:
            print '\ncreate_overlay_window defaults'

        try:
            ds.create_overlay_window(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    "7",
                    "8",
                    "9",
                    # clear_ink=False,
                    # delete_image=False,
                    # disable_page_turn=False,
                    # flash=False,
                    # redraw=False,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 110)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ("7", "8", "9"))

    def test_create_overlay_window_nondefault(self):
        if verbose:
            print '\ncreate_overlay_window non-default'

        try:
            ds.create_overlay_window(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    "7",
                    "8",
                    "9",
                    clear_ink=True,
                    delete_image=True,
                    disable_page_turn=True,
                    flash=True,
                    redraw=True,
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 110)
        self.assertEqual(send_data.options, 0x0000003e)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ("7", "8", "9"))

    def test_create_overlay_window_nondefault_w_wait(self):
        if verbose:
            print '\ncreate_overlay_window non-default & wait'
        notify_later()
        try:
            ds.create_overlay_window(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    "7",
                    "8",
                    "9",
                    clear_ink=True,
                    delete_image=True,
                    disable_page_turn=True,
                    flash=True,
                    redraw=True,
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 110)
        self.assertEqual(send_data.options, 0x0000003e)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ("7", "8", "9"))

    def test_create_overlay_window_opcode_property(self):
        self.assertEqual(ds.create_overlay_window.opcode, 110)

    # ===============================================================

    # Test set for "modify_overlay_window"
    #   Parameters: x_dest, y_dest, x_src, y_src, width_src, height_src,
    #         display_window_id:s, src_path:s
    #   Options: clear_ink, delete_image, flash, redraw
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-modifyoverlaywindow

    def test_modify_overlay_window_defaults(self):
        if verbose:
            print '\nmodify_overlay_window defaults'

        try:
            ds.modify_overlay_window(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    "7",
                    "8",
                    # clear_ink=False,
                    # delete_image=False,
                    # flash=False,
                    # redraw=False,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 111)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ("7", "8"))

    def test_modify_overlay_window_nondefault(self):
        if verbose:
            print '\nmodify_overlay_window non-default'

        try:
            ds.modify_overlay_window(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    "7",
                    "8",
                    clear_ink=True,
                    delete_image=True,
                    flash=True,
                    redraw=True,
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 111)
        self.assertEqual(send_data.options, 0x0000001e)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ("7", "8"))

    def test_modify_overlay_window_nondefault_w_wait(self):
        if verbose:
            print '\nmodify_overlay_window non-default & wait'
        notify_later()
        try:
            ds.modify_overlay_window(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    "7",
                    "8",
                    clear_ink=True,
                    delete_image=True,
                    flash=True,
                    redraw=True,
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 111)
        self.assertEqual(send_data.options, 0x0000001e)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4, 5, 6))
        self.assertEqual(send_data.char_args, ("7", "8"))

    def test_modify_overlay_window_opcode_property(self):
        self.assertEqual(ds.modify_overlay_window.opcode, 111)

    # ===============================================================

    # Test set for "close_overlay_window"
    #   Parameters: display_window_id:s
    #   Options: flash, redraw
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-closeoverlaywindow

    def test_close_overlay_window_defaults(self):
        if verbose:
            print '\nclose_overlay_window defaults'

        try:
            ds.close_overlay_window(
                    "1",
                    # flash=False,
                    # redraw=False,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 112)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1",))

    def test_close_overlay_window_nondefault(self):
        if verbose:
            print '\nclose_overlay_window non-default'

        try:
            ds.close_overlay_window(
                    "1",
                    flash=True,
                    redraw=True,
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 112)
        self.assertEqual(send_data.options, 0x00000006)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1",))

    def test_close_overlay_window_nondefault_w_wait(self):
        if verbose:
            print '\nclose_overlay_window non-default & wait'
        notify_later()
        try:
            ds.close_overlay_window(
                    "1",
                    flash=True,
                    redraw=True,
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 112)
        self.assertEqual(send_data.options, 0x00000006)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1",))

    def test_close_overlay_window_opcode_property(self):
        self.assertEqual(ds.close_overlay_window.opcode, 112)

    # ===============================================================

    # Test set for "change_config"
    #   Parameters: Variable:s, Value:s
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-changeconfig%5C

    def test_change_config_defaults(self):
        if verbose:
            print '\nchange_config defaults'

        try:
            ds.change_config(
                    "1",
                    "2",
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 120)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1", "2"))

    def test_change_config_nondefault(self):
        if verbose:
            print '\nchange_config non-default'

        try:
            ds.change_config(
                    "1",
                    "2",
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 120)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1", "2"))

    def test_change_config_nondefault_w_wait(self):
        if verbose:
            print '\nchange_config non-default & wait'
        notify_later()
        try:
            ds.change_config(
                    "1",
                    "2",
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 120)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ("1", "2"))

    def test_change_config_opcode_property(self):
        self.assertEqual(ds.change_config.opcode, 120)

    # ===============================================================

    # Test set for "erase_strokes_by_index"
    #   Parameters: start_index, end_index, page_id:s
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-erasestrokesbyindex%5C

    def test_erase_strokes_by_index_defaults(self):
        if verbose:
            print '\nerase_strokes_by_index defaults'

        try:
            ds.erase_strokes_by_index(
                    1,
                    2,
                    "3",
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 130)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2))
        self.assertEqual(send_data.char_args, ("3",))

    def test_erase_strokes_by_index_nondefault(self):
        if verbose:
            print '\nerase_strokes_by_index non-default'

        try:
            ds.erase_strokes_by_index(
                    1,
                    2,
                    "3",
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 130)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, (1, 2))
        self.assertEqual(send_data.char_args, ("3",))

    def test_erase_strokes_by_index_nondefault_w_wait(self):
        if verbose:
            print '\nerase_strokes_by_index non-default & wait'
        notify_later()
        try:
            ds.erase_strokes_by_index(
                    1,
                    2,
                    "3",
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 130)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2))
        self.assertEqual(send_data.char_args, ("3",))

    def test_erase_strokes_by_index_opcode_property(self):
        self.assertEqual(ds.erase_strokes_by_index.opcode, 130)

    # ===============================================================

    # Test set for "erase_ink_in_region"
    #   Parameters: x, y, width, height, page_id:s
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-eraseinkinregion%5C

    def test_erase_ink_in_region_defaults(self):
        if verbose:
            print '\nerase_ink_in_region defaults'

        try:
            ds.erase_ink_in_region(
                    1,
                    2,
                    3,
                    4,
                    "5",
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 131)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4))
        self.assertEqual(send_data.char_args, ("5",))

    def test_erase_ink_in_region_nondefault(self):
        if verbose:
            print '\nerase_ink_in_region non-default'

        try:
            ds.erase_ink_in_region(
                    1,
                    2,
                    3,
                    4,
                    "5",
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 131)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4))
        self.assertEqual(send_data.char_args, ("5",))

    def test_erase_ink_in_region_nondefault_w_wait(self):
        if verbose:
            print '\nerase_ink_in_region non-default & wait'
        notify_later()
        try:
            ds.erase_ink_in_region(
                    1,
                    2,
                    3,
                    4,
                    "5",
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 131)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1, 2, 3, 4))
        self.assertEqual(send_data.char_args, ("5",))

    def test_erase_ink_in_region_opcode_property(self):
        self.assertEqual(ds.erase_ink_in_region.opcode, 131)

    # ===============================================================

    # Test set for "doze"
    #   Parameters: none
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-doze%5C

    def test_doze_defaults(self):
        if verbose:
            print '\ndoze defaults'

        try:
            ds.doze(
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 140)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_doze_nondefault(self):
        if verbose:
            print '\ndoze non-default'

        try:
            ds.doze(
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 140)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_doze_nondefault_w_wait(self):
        if verbose:
            print '\ndoze non-default & wait'
        notify_later()
        try:
            ds.doze(
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 140)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_doze_opcode_property(self):
        self.assertEqual(ds.doze.opcode, 140)

    # ===============================================================

    # Test set for "sleep"
    #   Parameters: none
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-sleep%5C

    def test_sleep_defaults(self):
        if verbose:
            print '\nsleep defaults'

        try:
            ds.sleep(
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 141)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_sleep_nondefault(self):
        if verbose:
            print '\nsleep non-default'

        try:
            ds.sleep(
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 141)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_sleep_nondefault_w_wait(self):
        if verbose:
            print '\nsleep non-default & wait'
        notify_later()
        try:
            ds.sleep(
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 141)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_sleep_opcode_property(self):
        self.assertEqual(ds.sleep.opcode, 141)

    # ===============================================================

    # Test set for "set_doze_timer"
    #   Parameters: timeout
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-setdozetimer%5C

    def test_set_doze_timer_defaults(self):
        if verbose:
            print '\nset_doze_timer defaults'

        try:
            ds.set_doze_timer(
                    1,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 142)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1,))
        self.assertEqual(send_data.char_args, ())

    def test_set_doze_timer_nondefault(self):
        if verbose:
            print '\nset_doze_timer non-default'

        try:
            ds.set_doze_timer(
                    1,
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 142)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, (1,))
        self.assertEqual(send_data.char_args, ())

    def test_set_doze_timer_nondefault_w_wait(self):
        if verbose:
            print '\nset_doze_timer non-default & wait'
        notify_later()
        try:
            ds.set_doze_timer(
                    1,
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 142)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, (1,))
        self.assertEqual(send_data.char_args, ())

    def test_set_doze_timer_opcode_property(self):
        self.assertEqual(ds.set_doze_timer.opcode, 142)

    # ===============================================================

    # Test set for "do_test"
    #   Parameters: none
    #   Options: none
    #   Documentation at:
    #     http://eptwiki.rii.ricoh.com:8080/display/ePro/
    #       Display+Server+API#DisplayServerAPI-dotest

    def test_do_test_defaults(self):
        if verbose:
            print '\ndo_test defaults'

        try:
            ds.do_test(
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 255)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_do_test_nondefault(self):
        if verbose:
            print '\ndo_test non-default'

        try:
            ds.do_test(
                    request_id=1234,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        self.assertEqual(send_data.op_code, 255)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertEqual(send_data.request_id, 1234)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_do_test_nondefault_w_wait(self):
        if verbose:
            print '\ndo_test non-default & wait'
        notify_later()
        try:
            ds.do_test(
                    wait=True,
            )
        except DsMessageError, e:
            self.fail('Decoding exception: %s' % e)
        message = notify_check()
        self.assertFalse(message, message)
        self.assertEqual(send_data.op_code, 255)
        self.assertEqual(send_data.options, 0x00000000)
        self.assertNotEqual(send_data.request_id, 0)
        self.assertEqual(send_data.int_args, ())
        self.assertEqual(send_data.char_args, ())

    def test_do_test_opcode_property(self):
        self.assertEqual(ds.do_test.opcode, 255)


if __name__ == "__main__":
    import optparse
    op = optparse.OptionParser(description='Tests Display Server interface')
    op.add_option('-l', '--log-level', default='INFO',
        help='logging level (default: INFO)')
    op.add_option('-v', '--verbose', action='store_true', default=False,
        help='verbose output')
    op.add_option('--verbosity', type='int', default=1,
        help='unit test framework verbosity level (default: 1)')
    opts, args = op.parse_args()
    if args:
        op.error('No positional arguments expected')
    verbose = opts.verbose
    print "Testing Display Server interface...\n"
    try:
        display_server.logger.setLevel(getattr(logging, opts.log_level.upper()))
    except AttributeError:
        op.error('No such logging level name %r' % args[0])
    suite = unittest.TestLoader().loadTestsFromTestCase(
            TestDisplayServerInterface)
    unittest.TextTestRunner(verbosity=opts.verbosity).run(suite)
