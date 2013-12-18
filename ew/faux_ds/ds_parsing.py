# Copyright 2011 Ricoh Innovations, Inc.
from ew.util import ds_message, ew_logging as xlog
from ew.util.options_factory import BinaryOptions
import threading, socket, Queue, os

logger = xlog.getLogger('ew.faux_ds.ds_parsing')

class BinaryMessageReceiver(threading.Thread):
    def __init__(self, ds_message_class, sock):
        threading.Thread.__init__(self, name='ds_input')
        self.setDaemon(True)
        self._message_protocol = ds_message_class()
        self._input = sock
        self._queue = Queue.Queue()
        self._should_quit = False

    def options_as_dict(self, msg):
        true_options = msg.options.true_option_names()
        return dict([(name,True) for name in true_options])
    
    def run(self):
        while not self._should_quit:
            try:
                raw = self._input.recv(65565)
                msg = self._message_protocol.decode(raw)
                logger.debug('received and decoded %r', msg)
                #print 'message received %r' % msg
                self._queue.put(msg)
            except:
                #print 'failed!!!'
                logger.exception('error on read incoming')

    def get(self):
        return self._queue.get()
        
    def queue(self):
        return self._queue

    def stop_listenting(self):
        self._should_quit = True


class UDPInputSocket:
    def __init__(self,file_path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        if os.path.exists(file_path):
            os.remove(file_path)
        self.sock.bind(file_path)
        self.path = file_path
        self.file = self.sock.makefile('r')

    def __getattr__(self, name):
        return getattr(self.file, name)

class UDPOutputSocket:
    def __init__(self, file_path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.connect(file_path)
        self.path = file_path
        self.file = self.sock.makefile('w')

    def __getattr__(self, name):
        return getattr(self.file, name)

    
class BinaryMessageSender:
    def __init__(self, ds_message_class, a_socket):
        self._output = a_socket
        self._message_protocol = ds_message_class()
        self._options = BinaryOptions(
            **self._message_protocol.options_factory.option_bit_values)

    def send(self, opcode, int_args, char_args, request_id = 0, **options):
        opt_int = self._options.to_integer(**options)
        msg = self._message_protocol.encode(opcode, opt_int, request_id, int_args, char_args)
        self._output.send(msg)
        return msg

    
