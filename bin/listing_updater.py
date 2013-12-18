#!/usr/bin/python -OO

# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.

"""
@author Samantha Atkins

The ListenerUpdater is a daemon that tracks what the current
open document (if any) is and updates inbox and template 
directories on changes received via git-sync.  This daemon
defines a RPC server for receiving such messages and being 
queried regarding the current document (doc_id). The daemon
will adjust the Inbox and Template special DEC page images
in accordance with changes to documents in the Inbox and Templaces.
If the Inbox or Templates document is open then its DEC registers
to receive the corresponding messages instead of the daemon.

In accordance with DRI there will be a update_inbox.py and 
update_template_page.py that is shared with the Inbox and Template
DECs.
"""
from ew.util import comms, system_config, ew_logging
from ew.util import exclusive_document_lock
from collections import defaultdict
from ew.util import daemon, standard_doc_path
from ew.internal_decs.inbox_item_panel import InboxItemPanel as IP
from ew.internal_decs import INBOX_DOC_ID, TEMPLATES_DOC_ID, templates_document, inbox_document
import sys, os, pickle, types, threading

logger = ew_logging.getLogger('daemon.listing_updater')

#logging_config_path = os.path.join(system_config.config_dir, 'launcher_logger.config')

#whatever

class DocumentActions(dict):
    def note_action(self, name, arguments = None):
        self[name] = arguments


class ListingsUpdater(daemon.Daemon):
    _msg_fmt = '%(asctime)s.%(msecs)d:%(levelname)s:%(module)s %(message)s'
    _my_errors = os.path.join(system_config.log_dir, 'lu_errors.log')
    _inbox_path = os.path.join(system_config.internal_decs,INBOX_DOC_ID)
    _templates_path = os.path.join(system_config.internal_decs, TEMPLATES_DOC_ID)


    def __init__(self):
        daemon.Daemon.__init__(self, 'listing_updater')
        self._current_docid = None
        self.inbox_open = False
        self.templates_open = False
        self._direct_inbox = None
        self._direct_templates = None
        self._inbox_client = None
        self._templates_client = None
        self._backup_lock = threading.RLock()
        self._my_state_file = os.path.join(system_config.data_home, 'listing_updater.state')
        self.clear_bad_state_file()
        self._what_happened = self.load()
        self._sync_feeder = None
        self._sync_client = None
        self._launcher = None

    def clear_bad_state_file(self):
        """in dev we used a different format once which would break on the new one. Delete
        when so"""
        if os.path.isfile(self._my_state_file):
            try:
                x = self.load()
            except Exception:
                os.remove(self._my_state_file)

    def load(self):
        """load from saved state"""
        mydict = defaultdict(DocumentActions)
        with self._backup_lock:
            if os.path.isfile(self._my_state_file):
                with open(self._my_state_file, 'r') as f:
                    mydict = pickle.load(f)
            else:
                with open(self._my_state_file, 'w') as f:
                    pickle.dump(mydict,f, pickle.HIGHEST_PROTOCOL)
        return mydict

    def store(self):
        with self._backup_lock:
            with open(self._my_state_file, 'w') as f:
                pickle.dump(self._what_happened, f, pickle.HIGHEST_PROTOCOL)
                
    def sync_feeder(self):
        def bad_doc(doc):
            if type(doc) not in types.StringTypes:
                logger.debug('Docid should always be string but found %s. It will be removed', doc)
                return True
            else:
                path = standard_doc_path(doc)
                if not os.path.isdir(path):
                    logger.debug('document %s is no longer present. removing from doc_actions', doc)
                    return True
            return False

        def sanitize_what_happened():
            deleted = [k for k,v in self._what_happened.iteritems() if 'deleted' in v.keys()]
            to_check = [k for k in self._what_happened.keys() if k not in deleted]
            bad_docs = [k for k in to_check if bad_doc(k)]
            if bad_docs:
                for b in bad_docs:
                    self._what_happened.pop(b,None)
                self.store()

        sanitize_what_happened()
        docs = self._what_happened.keys()
        for doc in docs:
            #extra paranoia if doc disappeared in this tiny window after sanitization
            path = standard_doc_path(doc)
            stuff = self._what_happened.get(doc)
            if stuff:
                yield doc, tuple([(k,v) for k,v in stuff.iteritems()])
                
    def next_doc_to_sync(self):
        if not self._sync_feeder:
            self._sync_feeder = self.sync_feeder()
        try:
            next = self._sync_feeder.next()
        except StopIteration:
            next = None
            self._sync_feeder = None
        return next
    
    def sync_completed(self, docid):
        if self._what_happened[docid].get('submit',None):
            self.changed_document_status(docid, IP.Status.submitted)
        logger.debug('what happened before = %s', self._what_happened)
        self._what_happened.pop(docid, None)
        logger.debug('what happened after = %s', self._what_happened)
        self.store()
        
    def sync_did_not_process(self, docid, unprocessed):
        """Send by git-sync. unprocessed is a what_happened style
        dictionary of items it did not successfully process that 
        should be given back to it the next time it ask"""
        logger.debug('sync did not processes %s for document %s', unprocessed, docid)
        unprocessed = DocumentActions(unprocessed)
        if unprocessed.get('submit',None):
            self.document_submitted(docid)
        logger.debug('what happened before = %s', self._what_happened)
        if unprocessed:
            self._what_happened[docid] = unprocessed
        else:
            self._what_happened.pop(docid, None)
        logger.debug('what happened after = %s', self._what_happened)

        self.store()

    def sync_client(self):
        if not self._sync_client:
            self._sync_client = comms.create_sync_client()
        return self._sync_client

    def get_template_version(self, template_id):
        self.sync_client().get_template_version(template_id)

    def run(self):
        self.set_up_server()
        self.server.serve_forever()

    def set_inbox_open(self, bool):
        self.inbox_open = bool;

    def set_templates_open(self, bool):
        self.templates_open = bool;

    def set_up_server(self):
        self.server = comms.create_threaded_server(comms.LISTINGS_UPDATER_PORT)

        #sync telling me about items added or removed on tablet from server
        self.server.register_function(self.added_document)
        self.server.register_function(self.removed_document)
        self.server.register_function(self.removed_template)
        self.server.register_function(self.added_template)

        #sync processing of tablet changes methods
        self.server.register_function(self.next_doc_to_sync)
        self.server.register_function(self.sync_completed)
        self.server.register_function(self.sync_did_not_process)
        self.server.register_function(self.document_forked)

        #TODO remind Seth to call this
        self.server.register_function(self.document_being_submitted)
        self.server.register_function(self.downloading_documents)
        self.server.register_function(self.stopped_downloading)

        #convenience method for anything that cares what the current docid is
        self.server.register_function(self.current_docid)
        self.server.register_function(self.set_inbox_open)
        self.server.register_function(self.set_templates_open)
 
        #set by tablet on change of document
        self.server.register_function(self.set_current_docid)
        self.server.register_function(self.set_inbox_open)
        self.server.register_function(self.set_templates_open)
        
        #tablet adds changes of interest to sync
        self.server.register_function(self.tablet_request_refresh)
        self.server.register_function(self.tablet_cancelled_submit)
        self.server.register_function(self.tablet_deleted_document)
        self.server.register_function(self.tablet_instantiated_template)
        self.server.register_function(self.tablet_submitted_document)

    def document_forked(self, old_docid, new_docid):
        self._what_happened[new_docid].note_action('forked')
        self.store()

    def downloading_documents(self, docid_title_pairs, subdir='inbox'):
        #granted it looks wierd but both inbox() and templates() are now going to document runner
        try:
            self.inbox().downloading_documents(docid_title_pairs, subdir)
        except:
            logger.exception('downloading_documents %s failed',
                             docid_title_pairs)

    def stopped_downloading(self, doc_ids, subdir='inbox'):
        #granted it looks wierd but both inbox() and templates() are now going to document runner
        try:
            self.inbox().stopped_downloading(doc_ids, subdir)
        except:
            logger.exception('stopped_downloading(%s) failed',
                             doc_ids)
            
    def tablet_request_refresh(self):
        logger.debug('tablet requested refresh')
        def refresh_async():
            self.sync_client().sync_tablet()
        threading.Thread(target=refresh_async).start()
    
    def inbox(self):
        logger.debug('LU thinks inbox is open = %r', self.inbox_open)
        return self.inbox_client() if self.inbox_open else \
            self.inbox_document()

    def inbox_client(self):
        """messages the IndoxDocument via RPC
        within the running Inbox"""
        if not self._inbox_client:
            self._inbox_client = comms.create_local_client(comms.INBOX_PORT)
        return self._inbox_client

    def inbox_document(self):
        """opens the InboxDocument directly to 
        handle the work"""
        if not self._direct_inbox:
            self._direct_inbox = inbox_document.InboxDocument(self._inbox_path)
        return self._direct_inbox
        
    def templates(self):
        logger.debug('LU thinks templates is open = %r', self.templates_open)
        return self.templates_client() if self.templates_open else \
            self.templates_document()

    def templates_client(self):
        """messages the IndoxDocument via RPC
        within the running Inbox"""
        if not self._templates_client:
            self._templates_client = comms.create_local_client(comms.TEMPLATES_PORT)
        return self._templates_client

    def templates_document(self):
        """opens the InboxDocument directly to 
        handle the work"""
        if not self._direct_templates:
            self._direct_templates = templates_document.TemplatesDocument(self._templates_path)
        return self._direct_templates
        
    def tablet_instantiated_template(self, template_id, docid):
        version = 'whatever' #no real version info
        self._what_happened[docid].note_action('copy', dict(templateid=template_id,version=version))
        self.store()
        
    def record_delete(self, docid):
        if self._what_happened[docid].get('copy'):
            self._what_happened.pop(docid, None) #forget entire thing
        else:
            self._what_happened[docid].note_action('deleted')
        self.store()

    def tablet_deleted_document(self, docid):
        self.record_delete(docid)

#TODO persist and read _what_happened info on change and startup respectively
        
    def launcher(self):
        if not self._launcher:
            self._launcher = comms.create_launcher_client()
        return self._launcher

    def tablet_submitted_document(self, docid):
        """Send by DEC (Document) on receipt of non-overridden (by the DCE)
        on_submit"""
        logger.debug('submit doc started')
        self._what_happened[docid].note_action('submit')
        self.store()
        logger.debug('submit stored in lu info')
        self.tablet_request_refresh()
        logger.debug('sync kicked to handle submit')
        
    def tablet_cancelled_submit(self, docid):
        """Send by Inbox when a submit is cancelled by user reopening 
        the doc before the submit is in progress"""
        removed_from_queue = self._what_happened[docid].pop('submit', None)
        if removed_from_queue: 
            self.store()
        return removed_from_queue
    
    def added_document(self, docid):
        """Handle the addition of a new document"""
        try:
            self.inbox().add_document(docid)
        except:
            logger.exception('added_document(%s) failed',
                             docid)
            
    def removed_document(self, docid):
        """Handle the removal of a document"""
        self.record_delete(docid)
        try:
            self.inbox().remove_document(docid)
        except:
            logger.exception('added_document(%s) failed',
                             docid)
            
    def document_submitted(self, doc_id):
        self.changed_document_status(doc_id, \
                                     IP.Status.submitted)

    def document_being_submitted(self, doc_id):
        self.changed_document_status(doc_id, \
                                     IP.Status.submitted)

    def submit_complete(self, doc_id):
        self.changed_document_status(doc_id, \
                                     IP.Status.submittted)

    def changed_document_status(self, doc_id, new_status):
        """Handle document status change"""
        logger.debug('Attempting to change status(%s) <= %s', doc_id, new_status)
        try:
            self.inbox().change_document_status(doc_id, new_status)
        except:
            logger.exception('changed_document_status(%s,%s) failed',
                             doc_id, new_status)
                
    def added_template(self, template_id):
        """Handle addition of template"""
        try:
            self.templates().add_template(template_id)
        except:
            logger.exception('added_template(%s) failed',
                             template_id)
            
    def removed_template(self, template_id):
        """Handle template removal"""
        try:
            self.templates().remove_template(template_id)
        except:
            logger.exception('remove_template(%s) failed',
                             template_id)

    def current_docid(self):
        """Return the docid of the current document. Note that this daemon
        is dependent on others to keep this information up-to-date.  It merely
        caches it convenient to RPC clients"""
        return self._current_docid

    def set_current_docid(self, doc_id):
        """Set the docid of the current document.  This will likely be done by DEC
        but could possibly be done by launcher"""
        logger.debug("setting current docid to %s" % doc_id)
        if self._current_docid != doc_id:

            if self._current_docid == INBOX_DOC_ID and self._direct_inbox:
                self._direct_inbox.close()
                self._direct_inbox = None
            elif self._current_docid == TEMPLATES_DOC_ID and \
                self._direct_templates:
                self._direct_templates.close()
                self._direct_templates = None

            self._current_docid = doc_id
            self.inbox_open = self._current_docid == INBOX_DOC_ID
            self.templates_open = self._current_docid == \
                TEMPLATES_DOC_ID

if __name__ == '__main__':
    def usage(message=None):
        if message:
            print >> sys.stderr, message
        else:
            print >> sys.stderr, \
                "Launcher daemon\nArgs: start|stop|restart|foreground"
            sys.exit(2)

    if len(sys.argv) != 2:
        usage()

    arg = sys.argv[1]

    daemon = ListingsUpdater()
    if 'start' == arg:
        daemon.start()
    elif 'stop' == arg:
        daemon.stop()
    elif 'restart' == arg:
        daemon.restart()
    elif 'foreground' == arg:
        daemon.foreground()
    else:
        usage("Unknown command")
