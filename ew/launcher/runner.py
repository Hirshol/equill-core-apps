#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
from ds_event_dispatch import DSDatagramReceiver
from display_server import DSDatagramSender
from infobar import Infobar
import threading, os, types, pdb, time
from ew.util import comms, ew_logging as log, standard_doc_path, docid_from_path, system_config as sysconfig, login
from ew.util.resettable_timer import ResettableTimer
from ew.internal_decs.inbox_item_panel import InboxItemPanel as IP
from ew.memphis.file import MemphisFile
from sdk.document import Document
from sdk.delegate import Dec
from ew.util import tablet_config
if not os.getenv('emulate_tablet'):
    from ew.services.power import PowerService
    from ew.services.network import NetworkService
    from ew.services.audio import AudioService
    from ew.services.camera import Camera

import sys

config = tablet_config.Config()
loggin = login.Login()

logger = log.getLogger('ew.doc_runner')
runner_instance = None
runner_instance_lock = threading.Lock()
Internal_Subdir = 'internal_decs'
Running_Emulator = False

class DoesNothing:
    """does nothing for all methods"""
    def __getattr__(self, name):
        return self.do_nothing

    def do_nothing(self,*args):
        pass


class ConditionalLockRelease:
    """For a given document only release the loaded lock when all blocking operations
    have completed"""
    def __init__(self, document):
        self._doc_id = document.doc_id()
        self._lock = document._loaded_lock
        self._operations = []
        self._expired = False
        self._should_unlock_on_complete = False

    
    def add_operation(self, operation):
        if not self._expired:
            if not operation is self._operations:
                self._operations.append(operation)
            else:
                logger.warn('Document %s already has its log pending on operation %s',
                        self._doc_id, operation)

    def completed_operation(self, operation):
        if not self._expired:
            if operation in self._operations:
                self._operations.remove(operation)
            else:
                logger.debug('%s has no pending operation %s', self._doc_id, operation)
            if not self._operations:
                self._lock.release
                self._expired = True
                logger.debug('lock on %s released after last blocker was resolved', 
                             self._doc_id)

    def set_should_unlock(self):
        self._should_unlock_on_complete = True


class DocumentRunner:

    _instance_lock = threading.RLock()
    _instance = None

    @classmethod
    def instance(cls):
        with cls._instance_lock:
            if not cls._instance:
                xxx = DocumentRunner()
                cls._instance = xxx
            return cls._instance

    def __init__(self):
        self._to_ds = DSDatagramSender.instance()
        self._from_ds = DSDatagramReceiver(self)
        self._is_loading = False
        self._pending_operations = {}
        self._queued_submit = None
        self._tablet_title = None
        self._inbox = None
        self._templates = None
        self._settings = None
        self._document = None
        self._infobar = Infobar(self)
        self._known_windows = {}
        self._is_logged_in = False
        self._document_loading_lock = None #shared loaded lock on doc
        self._load_lock = threading.RLock() #only try one load at a time
        self._set_up_services()
        self._set_up_server()
        self._sync_LU_state()
        self._slept_document = None
        self._slept_in_pagenum = 0
        self._special_loading = dict(
            Inbox_Document = self.open_inbox,
            Templates_Document = self.open_templates,
            Settings_Document = self.open_settings)
        self._network_quiescent = threading.Event()
        self._ds_is_sleeping = threading.Event()
        self._pending_complete = threading.Event()
        self._pending_complete.set()
        self.setup_ready_sleep_timers()

        self._single_page_docs = dict (
            _state_low_battery = os.path.join(sysconfig.internal_decs, 'LowPower.memphis'),
            _state_sleeping = os.path.join(sysconfig.internal_decs, 'Sleep.memphis'),
            _state_login = os.path.join(sysconfig.internal_decs, 'Login.memphis'),
            _state_unprovisioned = os.path.join(sysconfig.internal_decs, 'NotProvisioned.memphis'),            
            _state_locked = os.path.join(sysconfig.internal_decs, 'Locked.memphis'),
            _state_off = os.path.join(sysconfig.internal_decs, 'BlankScreen.memphis'))
        for state in self._single_page_docs.keys():
            setattr(self, state, False)

    def setup_ready_sleep_timers(self):
        logger.debug('setting up sleep and power timers')
        with config.read_lock() as cf:
            ready_minutes = int(cf.get_option('core_app', 'minutes_until_ready', default = 5))
            sleep_minutes = int(cf.get_option('core_app', 'minutes_until_sleep', default=10))


        self._half_power = False
        self._ready_timer = ResettableTimer(ready_minutes * 60, self._half_power_CPU)
        self._sleep_timer = ResettableTimer(sleep_minutes * 60, self._do_sleep)
        logger.debug('timers ready')

    def _do_sleep(self):
        self.on_suspend('sleep')

    def _half_power_CPU(self):
        if not self._half_power:
            logger.debug('Entering ready CPU state')
            self.power().ready()
            self._half_power = True
            self._sleep_timer.start()

    def _full_power_CPU(self):
        if self._half_power:
            self._ready_timer.stop()
            self._sleep_timer.stop()
            logger.debug('Entering active CPU state')
            self.power().active()
            self._half_power = False


    def _on_activity(self):
        self._full_power_CPU()
        
    def _sync_LU_state(self):
        self._lu_client = comms.create_LU_client()
        self._lu_client.set_inbox_open(True)
        self._lu_client.set_templates_open(True)

    def listings_updater(self):
        return self._lu_client
    
            
    def set_log_level(self, level_name = None):
        import logging
        if not level_name:
            log_level = 'WARN'
            if config.has_option('core_app', 'log_level'):
                log_level = config.get('core_app', 'log_level')
        else:
            log_level = level_name

        logger.debug('logging level is %s', log_level)
        level = getattr(logging, log_level, logging.DEBUG)
        logger.root.setLevel(level)

    def _provisioning_ok(self):
        return config.is_provisioned() or config.is_developer_tablet()

    def display_first_screen(self, rebuild_attempted=False):
        try:
            if not self._provisioning_ok():
                self.require_provisioning()
                return
        
            self.set_log_level()
            self._state_locked = config.has_option('core_app', 'locked') and \
                config.getboolean('core_app', 'locked')

            if self._state_locked:
                self.disable_infobar()
                self._infobar.blank_image()
                self._load_single_page_doc('_state_locked')
                return
        
            if loggin.require_login():
                self.request_login()
                return
        
            self.open_inbox()
        except:
            logger.exception('failed to open first screen. retrying after rebuilding internal decs')
            if not rebuild_attempted:
                self._rebuild_internal_decs()
                self.display_first_screen(True)
            else:
                logger.critical('rebuild of internals attempted but did not resolve the issue')
                sys.exit()

    def _load_single_page_doc(self, condition_name):
        path = self._single_page_docs.get(condition_name)
        if path:
            self.load_document(path)
            self._document.mask_strokes(True)

    def _set_up_services(self):
        #from ew.services.camera import Camera
        logger.debug('setting up services')
        if os.getenv('emulate_tablet'):
            self._camera = DoesNothing()
            self._network = DoesNothing()
            self._powermgr = DoesNothing()
            self._location = DoesNothing()
        else:
            logger.debug('setting up camera')
            self._camera = Camera.instance() #do not make runner a client
            logger.debug('setting up network')
            self._network = NetworkService()
            logger.debug('creating powermgr')
            self._powermgr = PowerService()
            logger.debug('created powermgr')
            self._location = DoesNothing()
            self._audio = AudioService()
        self._network.on_connection_info(self.handle_connection_info)
        self._network.start()
        self._network.get_conn_info()
        
        self._powermgr.on_fuel_gauge_change(self.on_fuel_gauge_change)
        self._powermgr.on_power_short_release(self.on_suspend)
        self._powermgr.on_suspend(self.on_suspend)
        self._powermgr.on_wakeup(self.on_suspend)
        self._powermgr.on_battery_warning(self.battery_warning)
        self._powermgr.start()
        self._audio.start()
        logger.debug('finished setting up services')

#        self._powermgr.on_power_long_hold(self.blank_screen)
        #self._network.add_callback('on_network_status', self._infobar.set_network_info)
        # this has to be done after all services are ready

    def handle_connection_info(self, signal, conn_type, ssid_info, address, *args):
        signal = min(3, signal // 25)
        if self._network.is_airplane_mode():
            conn_type = "airplane"
        else:
            if address == 'Roam':
                conn_type = '3GR'
        logger.debug('connection info: %s, %s, %s, %s', signal, conn_type, ssid_info, address)
        self._infobar.set_network_info(conn_type, signal, ssid_info, address)
        if (not conn_type) or conn_type == "airplane":
            self._network_quiescent.set()


    def blank_screen(self, *args):
        self.disable_infobar()
        self._infobar.blank_image()
        self._load_document(os.path.join(sysconfig.internal_decs, 'BlankScreen.memphis'))

    def handle_sleep_wake(self, *args):
        self.sleep_tablet(not self._state_sleeping)

    def lock_tablet(self, lock_it = True):
        self.handle_state_change('_state_locked', lock_it)

    def sleep_tablet(self, sleep_now = True):
        logger.debug('sleep tablet: %s', sleep_now)
        if (not self._state_locked):
            self.handle_state_change('_state_sleeping', sleep_now)
#        if (not self._state_locked) and self._provisioning_ok():
#            self.handle_state_change('_state_sleeping', sleep_now)

    def request_login(self, login = True):
        if not (self._state_locked or self._state_unprovisioned):
            self.handle_state_change('_state_login', login)
            
    def require_provisioning(self, provision = True):
        if not self._state_locked:
            self.handle_state_change('_state_unprovisioned', provision)

    def battery_warning(self, low_power=True):
        self.handle_state_change('_state_low_battery', low_power)

    def handle_state_change(self, condition_name, bool_value):
        internal = getattr(self, condition_name)
        if internal != bool_value:
            setattr(self, condition_name, bool_value)
            if bool_value:
                self.disable_infobar()
                self._infobar.blank_image()
                self._load_single_page_doc(condition_name)
            else:
                self.enable_infobar()
                self._infobar.restore_image()
                self.open_first_document()
            
    def open_inbox_with_infobar(self):
        self.open_first_document()
        self._infobar.restore_image()
        self.enable_infobar()
        
    def open_first_document(self):
        if self._slept_document:
            doc = self._slept_document
            self._slept_document = None
            self.load_document(doc, self._slept_in_page)
        else:
            self.open_inbox()
    
    def infobar(self):
        return self._infobar

    def camera(self):
        return self._camera

    def network(self):
        return self._network
    
    def power(self):
        return self._powermgr

    def location(self):
        return self._location

    def audio(self):
        return self._audio

    def _is_special_docid(self, docid):
        from ew.internal_decs import INBOX_DOC_ID, TEMPLATES_DOC_ID,\
                SETTINGS_DOC_ID, PROVISION_DOC_ID, LOGIN_DOC_ID, LEGAL_DOC_ID,\
                REGULATORY_DOC_ID, LICENSE_DOC_ID
        return docid in (INBOX_DOC_ID, TEMPLATES_DOC_ID, SETTINGS_DOC_ID, \
                PROVISION_DOC_ID, LOGIN_DOC_ID, LEGAL_DOC_ID, \
                REGULATORY_DOC_ID, LICENSE_DOC_ID)

    def _is_special_document(self, document):
        return self._is_special_docid(document.doc_id())

    def on_stroke(self, index, flags, window_id, millis, points):
        window = None
        self._on_activity()
        if window_id:
            window_id = window_id.split('.')[0]
        if self.infobar().owns_stroke(index, flags, window_id, millis, points):
            window = self._infobar
        elif self._document:
            window = self._document.window_handling_stroke_in(window_id)
            if not self._is_special_document(self._document):
                self.inbox().mark_modified_if_new(self._document.doc_id())

        if window:
            window.on_stroke(index, flags, millis, points)
        else:
            logger.warn('no window to accept stroke to window id %s', window_id)
        self._ready_timer.start()

    def on_page(self, page_id):
        self._on_activity()
        self._infobar.update_using_region_of_page(page_id)

        if self._is_special_document(self._document):
            self._document.mask_strokes(True)

        if self._queued_submit:
            self.listings_updater().tablet_submitted_document(self._queued_submit)
            self._queued_submit = 0

        if self._document:
            self._document.on_page(page_id)
        self._ready_timer.start()

    def submit_when_ready(self, doc_id):
        self._queued_submit = doc_id
        self.inbox().change_document_status(doc_id, IP.Status.submitted)
        self.open_inbox()

    def on_submit(self):
        if self._document and not self._state_sleeping:
            self._document.on_submit()

    def on_read_complete(self, request_id):
        self._to_ds.handle_request_completion(request_id)

    def on_render_complete(self, request_id):
        self._to_ds.handle_request_completion(request_id)

    def on_error(self, request_id, error_code):
        self._to_ds.handle_request_completion(request_id, error_code)

    def on_stroke_file_ready(self, page_id, stroke_file_path):
        if stroke_file_path.startswith('/data/internal_decs'): return

        mpath = stroke_file_path.split('.memphis/')[0] + '.memphis'
        logger.debug('stroke_file_ready should go to %s', mpath)
        with MemphisFile(mpath) as mf:
            mf.add_stroke_file(stroke_file_path)

    def on_landscape(self):
        pass #not supposed to care by design

    def on_portrait(self):
        pass #not supposed to care by design

    def _suspend_countdown(self, wait_seconds=30):
        if self._trying_to_suspend:
            self._network_quiescent.clear()
            self._network_quiescent.wait(wait_seconds)
        
    def _kill_radios(self):
        if True: #not os.getenv('is_developer_tablet'):
            self.network().rfkill()
        else: 
            logger.warn('would have killed wifi to here')
        
    def _sleep_DS(self):
        self._ds_is_sleeping.clear()
        self._to_ds.sleep()
        self._ds_is_sleeping.wait(10)
    
    def _wait_to_really_sleep(self):
        def countdown():
            self._sleep_DS()
            self._suspend_countdown()
            if self._trying_to_suspend: #it didn't get cancelled by now
                logger.debug('killing radios and doing can suspend')
                self._kill_radios()
                self.power().can_suspend('sleep')
        t = threading.Thread(target = countdown)
        t.setDaemon(True)
        return t

    def _cancel_sleep_timers(self):
        self._trying_to_suspend = False
        self._ds_is_sleeping.set()
        self._network_quiescent.set()

    def _wait_to_really_halt(self):
        def countdown():
            self._pending_complete.wait(15)
            self._suspend_countdown()
            self.power().can_suspend('halt')
        t = threading.Thread(target = countdown)
        t.setDaemon(True)
        return t

        
    def on_suspend(self, kind, vait_seconds=30):
        logger.debug('received suspend(%s) is_sleep: %s, sleeping: %s', kind, kind == 'sleep',
                     self._state_sleeping)

        suspend_action = None
        self._trying_to_suspend = True
        if (kind == 'sleep'): 
            if not self._state_sleeping:
#                if not self._is_special_document(self._document):
                self._slept_document = self._document.path
                self._slept_in_page = self._document.current_page.page_index
                suspend_action = self._wait_to_really_sleep()
                self.handle_sleep_wake()
            else:
                self._cancel_sleep_timers()
                if loggin.require_login():
                    self._state_sleeping = False
                    self._load_single_page_doc('_state_login')
                else:
                    self.handle_sleep_wake()

        elif kind == 'halt':
            self.blank_screen()
            suspend_action = self._wait_to_really_halt()

        if suspend_action:
            suspend_action.start()
        
    def on_wake(self, kind):
        self._trying_to_suspend = False
        if kind == 'sleep' and self._state_sleeping:
            self.sleep_tablet(False)
            self._open_last_document()
            
    def on_sleep(self):
        self._ds_is_sleeping.set()

    def on_doze(self):
        pass #TBD

#    def on_wake(self):
#        self.sleep_tablet(False)

    def on_viewport_change(self, start_index, end_index):
        if self._document:
            self._document.on_viewport_change(start_index, end_index)

    def on_shutdown(self):
        pass #TBD

    def add_document_pending_operation(self, operation_name):
        """adds a pending operation before releasing the current loaded document's loaded lock"""
        with self._instance_lock:
            docid = self._document.doc_id()
            pending = self._pending_operations.get(docid, None)
            if not pending:
                self._pending_operations[docid] = pending = ConditionalLockRelease(self._document)
            pending.add_operation(operation_name)
            self._pending_complete.clear()

    def completed_document_pending_operation(self, docid, operation_name):
        with self._instance_lock:
            pending = self._pending_operations.get(docid, None)
            if pending:
                pending.completed_operation(operation_name)
                if pending._expired:
                    self._pending_operations.pop(docid, None)
                    if not self._pending_operations:
                        self._pending_complete.set()

    def _release_document_lock(self, document):
        with self._instance_lock:
            docid = document.doc_id()
            pending = self._pending_operations.get(docid, None)
            if pending:
                pending.set_should_unlock()
                logger.debug('lock on %s will be released when blockers are resolved',
                             docid)
            else:
                self._document._loaded_lock.release()
                logger.debug('lock on %s released as requested with no blockers', docid)
            
    def _close_document(self):
        if self._document:
            self._document.on_close()
            if not self._is_special_document(self._document):
                self._release_document_lock(self._document)
#                if hasattr(self._document, '_loaded_module'):
#                    sys.modules.pop(self._document._loaded_module.__name__)
                del self._document
            self._document = None

    def _current_page(self):
        return self._document.current_page if self._document else None

    def unlock_document(self):
        self._document._is_submit_locked = False

    def _switch_to_document(self, document, page_number = 0, **flags):
        if document:
            self._close_document()
            self._document = document
            special = self._is_special_document(self._document)
            if not special:
                self._infobar.set_active_button(None)
            if self._document._is_submit_locked:
                self._infobar.lock_document()
            else:
                logger.debug('document %s is not locked', self._document.title())
            self._ds_load(page_number = page_number, mask_ink = special)
            self._document.refresh() 

    def reload_current_document(self, page_number = 0):
        """tells DS to relead the current document and jump to given page number.
        Temporary hack until insert page is propreply supported"""
        self._to_ds.load_document(page_number, self._document.path)
        
    def set_title(self, title):
        self._tablet_title = title
        self._infobar.set_title(title)

    def tablet_title(self):
        if not self._tablet_title or self._tablet_title == 'Unknown User':
            self._tablet_title = config.get('session', 'name', 'Unknown User')
        return self._tablet_title

    def _ds_load(self, page_number, **flags):
        title = self.tablet_title() if self._is_special_document(self._document) else self._document.title()
        self._infobar.set_title(title)
        self._to_ds.load_document(page_number, self._document.path, **flags) #always use first page

    def open_inbox(self):
        self._infobar.mark_inbox_active()
        with self._load_lock:
            inbox = self.inbox()
            if self._document == inbox:
                self._document.refresh()
            else:
                self._switch_to_document(inbox)

    def inbox(self):
        from ew.internal_decs.inbox_document import InboxDocument, \
            InboxDelegate
        with self._instance_lock:
            if not self._inbox:
                self._inbox = \
                    self._open_doc_id('Inbox_Document',
                                        document_class = InboxDocument,
                                        delegate_class = InboxDelegate)
            #else:
            #    self._inbox.refresh()

        return self._inbox

    def open_templates(self):
        with self._load_lock:
            self._switch_to_document(self.templates())

    def _get_templates(self):
        if not self._templates:
            return self.templates()
        else:
            return self._templates

    def _get_inbox(self):
        if not self._inbox:
            return self.inbox()
        else:
            return self._inbox

    def templates(self):
        from ew.internal_decs.templates_document import TemplatesDocument, \
            TemplatesDelegate
        with self._instance_lock:
            if not self._templates:
                self._templates = \
                    self._open_doc_id('Templates_Document',
                                        document_class = TemplatesDocument,
                                        delegate_class = TemplatesDelegate)
           # else:
           #     self._templates.refresh()

            return self._templates

    def open_settings(self):
        with self._load_lock:
            self._switch_to_document(self.settings())

    def settings(self):
        from ew.internal_decs.settings_delegate import SettingsDelegate
        from ew.internal_decs.settings_document import SettingsDocument
        with self._instance_lock:
            if not self._settings:
                self._settings = self._open_doc_id(
                    doc_id='Settings_Document',
                    document_class = SettingsDocument,
                    delegate_class = SettingsDelegate)
           # else:
           #     self._settings.refresh()

            return self._settings

    def is_loading(self):
        return self._is_loading

    def _load_document(self, path, page_number = 0, **flags):
        with self._load_lock:
            try:
                self._is_loading = True
                document = self._open_document(path)
                if document:
                    self._switch_to_document(document, page_number, **flags)
                self._is_loading = False
            except:
                self._is_loading = False
                logger.exception('failed to load document @ %s', path)

    def _open_doc_id(self, doc_id, delegate_class, document_class = Document):
        #only called for special documents
        return self._open_document(
            standard_doc_path(doc_id,
                              Internal_Subdir),
            special=True,
            delegate_class = delegate_class,
            document_class = document_class)

    def _open_document(self, path, special=False,
                       document_class= Document,
                       delegate_class= Dec):
        document = None
        accept_custom = path.startswith('/data/internal_decs') or \
            config.is_developer_tablet()
        if os.path.exists(path):
            def get_classes_and_lock():
                mfile = MemphisFile(path)
                mfile.open()
#                pdb.set_trace()
                alock = mfile.get_lock('loaded', exclusive=False)
                try:
                    alock.acquire(non_blocking=True)
                except alock.LockUnavailableError:
                    logger.debug('document at %s is temporarily busy',
                                 path)
                    return None
                code_path = os.path.join(path, 'memphis.document.d', 'code',
                                     'dec.py')
                document_class, delegate_class = Document, Dec
                is_custom = os.path.exists(code_path)
                if is_custom and accept_custom:
                    import imp
                    foo = imp.load_source('foo', code_path)
                    document_class = foo.document_class
                    if not document_class:
                        document_class = Document
                    delegate_class = foo.delegate_class
                mfile.close()
                return document_class, delegate_class, alock

            if not special:
                classes_and_info = get_classes_and_lock()
                document_class, delegate_class, load_lock = classes_and_info
            else:
                load_lock = None
            logger.debug('loading document %s with doc_class %s, delegate_class %s',
                         path, document_class.__name__, delegate_class.__name__)
            document = document_class(path, delegate_class=delegate_class, runner=self)
            logger.debug('finished part 1 of loading document')
            document._loaded_lock = load_lock
        else:
            logger.error('No memphis document found at %s. Ignored.', path)
            return None

        if not document.previously_loaded():
            document.on_first_load()
        document.on_load()
        document.save_page_changes()

        return document

    def _load_internal_document(self, doc_id):
        doc = self._open_document(doc_id)
        self._switch_to_document(doc)

    def start_services(self):
        logger.debug('starting DocumentRunner services')
        self._rpc_thread.start() #start XML server
        self._from_ds.start_service() #start DS event loop

    def stop_services(self):
        logger.warn('Shutting down DocumentRunner services')
        self._to_ds.clear() #clear any waiters on DS response
        self._from_ds.stop_service()  #stop listening to DS
        self._close_document() #close and clean up current document
        self._rpc_thread.server.shutdown() #stop XMLRPC server

    ### Server setup and methods ###
    def _set_up_server(self):
        server = comms.create_threaded_server(comms.LAUNCHER_PORT)
        self._rpc_thread = comms.ServerThread('doc_runner', server)
        self._add_ds_delegates(server)
        server.register_function(self.open_inbox)
        server.register_function(self.open_inbox_with_infobar)
        server.register_function(self.load_document)
        server.register_function(self.submit_when_ready)
        server.register_function(self.set_title)
        server.register_function(self.synchronous_load_document)
        server.register_function(self.stop_services)
        server.register_function(self.enable_infobar)
        server.register_function(self.disable_infobar)
        server.register_function(self.lock_tablet)
        server.register_function(self.sleep_tablet)
        server.register_function(self.blank_screen)
        server.register_function(self.request_login)
        server.register_function(self.battery_warning)
        server.register_function(self.require_provisioning)
        server.register_function(self.set_log_level)
        server.register_function(self.add_document_pending_operation)
        server.register_function(self.completed_document_pending_operation)
        server.register_function(self.downloading_documents)
        server.register_function(self.stopped_downloading)
        server.register_function(self.legal_document)
        server.register_function(self.setup_ready_sleep_timers)
        
        self._add_inbox_delegates(server)
        self._add_templates_delegates(server)
        #temporary to test functionality
        server.register_function(self._infobar.set_network_info)

    def enable_infobar(self):
        self._infobar.enable()

    def disable_infobar(self):
        self._infobar.disable()

    def load_document(self, doc_path, page_number=0, **flags):
        doc_id = docid_from_path(doc_path)
        if doc_id in self._special_loading:
            self._special_loading[doc_id]()
        else:
            self._load_document(doc_path, page_number = page_number)

    def synchronous_load_document(self, doc_path, page_number = 0):
        self.load_document(doc_path, page_number, wait=True)

    def downloading_documents(self, docid_title_pairs, subdir='inbox'):
        if subdir not in ('inbox', 'templates'):
            logger.warn('ignoring downloading documents to subdirectory %s', subdir)
            return
        target = self._get_inbox() if subdir == 'inbox' else self._get_templates()
        target.downloading_documents(docid_title_pairs)

    def stopped_downloading(self, docids, subdir='inbox'):
        if subdir not in ('inbox', 'templates'):
            logger.warn('ignoring downloading documents to subdirectory %s', subdir)
            return
        target = self._get_inbox() if subdir == 'inbox' else self._get_templates()
        target.stopped_downloading(docids)

    def legal_document(self, type):
        if type in ['Legal', 'License', 'Regulatory']:
            legal_doc_id = '%s.memphis' % type
            legal_doc = os.path.join(sysconfig.internal_decs, legal_doc_id)
            self.load_document(legal_doc)
            self._document.mask_strokes(True)

    def _add_inbox_delegates(self, server):
        def make_delegate(name):
            def delegate(*args, **kwargs):
                inbox = self._get_inbox()
                fun = getattr(inbox, name)
                logger.debug('calling inbox.%s%s', fun.__name__, args)
                res = fun(*args, **kwargs)
                inbox.save_page_changes()
                return res
            delegate.__name__ = name
            return delegate
        server.register_function(make_delegate('add_document'))
        server.register_function(make_delegate('remove_document'))
        server.register_function(make_delegate('change_document_status'))

    def immediately_add_to_inbox(self, doc_id):
        self._get_inbox().add_document(doc_id)

    def _add_templates_delegates(self, server):
        def make_delegate(name):
            def delegate(*args, **kwargs):
                templates = self._get_templates()
                fun = getattr(templates, name)
                res =  fun(*args, **kwargs)
                templates.save_page_changes()
                return res
            delegate.__name__ = name
            return delegate
        server.register_function(make_delegate('add_template'))
        server.register_function(make_delegate('remove_template'))

    def _add_ds_delegates(self, server):
        """Create a delegate method in the Operations class to every method defined
           in module display_server."""
        def make_delegate(function_name, function):
            def delegate(self, *args, **kwargs):
                # since XMLRPC does not handle keyword arguments fake
                # it here. Note this would be a problem if any of the
                # wrapped calls take a dict last argument.  Not the
                # case here but worth remembering.  Call the DS methods
                # through the launcher with a dict last argument if
                # you want non-default vertions of any DS options
                if args and isinstance(args[-1],dict) and not kwargs:
                    kwargs = args[-1]
                    args = args[:-1]
                #logger.debug('Delegating %s(*args=%r, **kwargs=%r)',
                #        function_name, args, kwargs)
                return getattr(self._to_ds, function_name)(*args, **kwargs)
            delegate.__name__ = function_name
            return delegate


        for k, v in self._to_ds.__dict__.iteritems():
            is_ds_op = type(v) is types.FunctionType and not hasattr(self, k)
            is_ds_op = is_ds_op and hasattr(v, 'opcode')
            if is_ds_op:
                fun = make_delegate(k, v)
                server.register_function(fun)

    def __getattr__(self, name):
        if hasattr(self, '_to_ds'):
            return  getattr(self._to_ds, name)
        raise AttributeError()

    #service callbacks

    def on_fuel_gauge_change(self, *args):
        status, level = args[0], int(args[1])
        is_charging = status != 'Discharging'
        level = min(4, level // 20)
        if level == -1: level = 4 #hack for bad PM value
        logger.debug('received fuel gauge change to level %r, status %s', level, status)
        self._infobar.set_battery_level(level, is_charging)
        if self._state_low_battery and is_charging:
            self.battery_warning(False)

    def _rebuild_internal_decs(self):
        path = '/var/cache/ews/payloads/home.tar.bz2'
        def clear_internal_doc(doc_attr):
            doc = getattr(self, doc_attr, None)
            if doc:
                del doc
                setattr(self, doc_attr, None)
        if os.path.exists(path):
            if self._document:
                self._document.close()
            clear_internal_doc('_inbox')
            clear_internal_doc('_templates')
            clear_internal_doc('_settings')
            if self._document_loading_lock and self._document_loading_lock.acquired:
                self._document_loading_lock.release()
            command = 'cd /data;rm -rf internal_decs;tar xjf %s  ./internal_decs' % path
            os.system(command)
        else:
            logger.debug('skeleton files were not found, expected %s', path)

def main():
    args = sys.argv
    print 'args', args
    runner = DocumentRunner.instance()
    runner.start_services()
    runner.display_first_screen()
    time.sleep(999999999.0) #forever nearly..

def shutdown():
    runner = DocumentRunner.instance()
    runner.stop_services()

if __name__ == '__main__':
    main()

