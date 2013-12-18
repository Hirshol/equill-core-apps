PyCrust 0.9.8 - The Flakiest Python Shell
Python 2.7.1+ (r271:86832, Apr 11 2011, 18:13:53) 
[GCC 4.5.2] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import sys
>>> sys.path
['', '/home/samantha/work/ricoh/root/usr/local/lib/ew/python', '/usr/lib/python2.7', '/usr/lib/python2.7/plat-linux2', '/usr/lib/python2.7/lib-tk', '/usr/lib/python2.7/lib-old', '/usr/lib/python2.7/lib-dynload', '/usr/local/lib/python2.7/dist-packages', '/usr/lib/python2.7/dist-packages', '/usr/lib/python2.7/dist-packages/PIL', '/usr/lib/pymodules/python2.7/gtk-2.0', '/usr/lib/python2.7/dist-packages/gst-0.10', '/usr/lib/python2.7/dist-packages/gtk-2.0', '/usr/lib/pymodules/python2.7', '/usr/lib/pymodules/python2.7/ubuntuone-control-panel', '/usr/lib/pymodules/python2.7/ubuntuone-client', '/usr/lib/pymodules/python2.7/libubuntuone', '/usr/lib/pymodules/python2.7/ubuntuone-storage-protocol', '/usr/lib/python2.7/dist-packages/wx-2.8-gtk2-unicode']
>>> import ew.faux_ds.ds_parsing as ds
>>> from ew.util.ds_message import DsMessage
>>> input = ds.file_based_UDP_input('~/trial.socket')
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py", line 32, in file_based_UDP_input
    sock.bind(file_path)
  File "/usr/lib/python2.7/socket.py", line 224, in meth
    return getattr(self._sock,name)(*args)
error: [Errno 2] No such file or directory
>>> input = ds.file_based_UDP_input('/home/samantha/trial.socket')
>>> receiver = ds.BinaryMessageReceiver(DsMessage, input)
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py", line 7, in __init__
    self.setDaemon(True)
  File "/usr/lib/python2.7/threading.py", line 720, in setDaemon
    self.daemon = daemonic
  File "/usr/lib/python2.7/threading.py", line 711, in daemon
    raise RuntimeError("Thread.__init__() not called")
RuntimeError: Thread.__init__() not called
>>> reload ds
<module 'ew.faux_ds.ds_parsing' from '/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py'>
>>> input = ds.file_based_UDP_input('/home/samantha/trial.socket')
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py", line 32, in file_based_UDP_input
    sock.bind(file_path)
  File "/usr/lib/python2.7/socket.py", line 224, in meth
    return getattr(self._sock,name)(*args)
error: [Errno 98] Address already in use
>>> input
<socket._fileobject object at 0x2345550>
>>> receiver = ds.BinaryMessageReceiver(DsMessage, input)
>>> receiver.start()
>>> receiver.is_alive
<bound method BinaryMessageReceiver.isAlive of <BinaryMessageReceiver(ds_input, started daemon 139979801409280)>>
>>> receiver.is_alive()
True
>>> output = ds.file_based_UDP_output('/home/samantha/trial.socket')
>>> sender = ds.BinaryMessageSender(DsMessage, output)
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py", line 47, in __init__
    self._options = BinaryOptions(self._message_protocol.option.options_bit_values)
NameError: global name 'BinaryOptions' is not defined
>>> reload ds
<module 'ew.faux_ds.ds_parsing' from '/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py'>
>>> sender = ds.BinaryMessageSender(DsMessage, output)
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py", line 48, in __init__
    self._options = BinaryOptions(self._message_protocol.option.options_bit_values)
AttributeError: 'DsMessage' object has no attribute 'option'
>>> sender = ds.BinaryMessageSender(DsMessage, output)
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py", line 48, in __init__
    self._options = BinaryOptions(self._message_protocol.options.options_bit_values)
AttributeError: 'DsMessage' object has no attribute 'option'
>>> reload ds
<module 'ew.faux_ds.ds_parsing' from '/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py'>
>>> sender = ds.BinaryMessageSender(DsMessage, output)
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py", line 48, in __init__
    self._options = BinaryOptions(self._message_protocol.options.options_bit_values)
AttributeError: 'DsMessage' object has no attribute 'options'
>>> reload ds
<module 'ew.faux_ds.ds_parsing' from '/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py'>
>>> sender = ds.BinaryMessageSender(DsMessage, output)
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py", line 48, in __init__
    self._options = BinaryOptions(**self._message_protocol.options_bit_values)
AttributeError: 'DsMessage' object has no attribute 'options_bit_values'
>>> reload ds
<module 'ew.faux_ds.ds_parsing' from '/home/samantha/work/ricoh/root/usr/local/lib/ew/python/ew/faux_ds/ds_parsing.py'>
>>> sender = ds.BinaryMessageSender(DsMessage, output)
>>> sender.send(105, (1, 45), ('foo', 'bar'))
>>> receiver.is_alive()
True
>>> msg = sender._message_protocol.encode(105, 0, 0, (1,45), ('foo'))
>>> msg
'N\x01\x1c\x13\x00\x00\x00\x00c\x00\x00\x00\x00\x00\x00\x00i\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00-\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00foo'
>>> sender._output.write(msg)
>>> sender._output.flush()
>>> msg = sender._message_protocol.encode(105, 0, 0, (1,45), ('foo',))
>>> sender = ds.BinaryMessageSender(DsMessage, output)
>>> sender._output.write(msg)
>>> sender._output.flush()
>>> receiver.is_alive()
False
>>> 