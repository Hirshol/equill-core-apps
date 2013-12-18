#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
"""Utilities related to binary function call message protocol

Provides facilities to decode and encode messages conforming to the EW
binary format. See the format_description method below for a specification
of the format.

Designed for subclassing such that certain properties of the message type
(such as option names and values) can be customized. See the comments for
class EwBinaryMessage.

The "decode" and "read_from_stream" methods return an EwDecodedMessage
object that contains the message components:
    'total_length',   # Total length of whole message (int)
    'op_code',        # Op code integer value (int)
    'options',        # Option bits as Options object, with each option's
                      # boolean value in a property named for the option
    'request_id',     # Request ID integer value (int)
    'int_args',       # List of int argument values as integers (list of int)
    'char_args'       # List of char argument values as strings (list of str)

"""

from struct import pack, unpack, calcsize, error as struct_error
from itertools import chain

from ew.util.options_factory import OptionsFactory

class EwBinaryMessage(object):
    """Utilities related to binary function call message protocol

    Things intended for possible modification by subclasses:
      - magic_number: Magic number (default: 0x131C014E)
      - endian: Byte order and alignment character as defined for the Python
        "struct" module
        (http://docs.python.org/release/2.6.6/library/
            struct.html#byte-order-size-and-alignment)
        (default: '@' (native))
      - option_bit_values: Option bit names and values
        (default: no options defined)

    """

    __slots__ = ('magic_number', 'endian', 'option_bit_values',
            'header_format', 'header_length', 'options_factory')

    def __init__(self, magic_number=0x131C014E, endian='@',
            option_bit_values=None):
        """
        "option_bit_values" is a dict with entries:
            option_name: option_bit_mask_value
        """
        self.magic_number = magic_number
        self.endian = endian
        self.option_bit_values = (option_bit_values if
                option_bit_values is not None else {})
        self.header_format = self.endian + '2L'
        self.header_length = calcsize(self.header_format)
        self.options_factory = OptionsFactory(**self.option_bit_values)

    def format_description(self):
        """Return a text description of the binary protocol.
        (As well as serving as source code documentation)
        """
        return """\
# %s message protocol (in pseudo-C):
#
# int magic_word      // 0x%08x
# int total_length    // Length in bytes of *all* fields
# int op_code         // Operation code
# int options         // Options bits
# int request_id      // Request ID (0 is null request_id)
#
# int integer_parameter_count    // Count of integer parameters (IPC)
# int char_parameter_count       // Count of char parameters (CPC)
#
# int integer_parameter_1        // First integer parameter value
# ...
# int integer_parameter_IPC      // Last  integer parameter value
#
# int char_parameter_length_1    // First char parameter length in bytes
# ...
# int char_parameter_length_CPC  // Last char parameter length in bytes
#
# char[] char_data_1             // First char parameter data
# char[] char_data_2             // First char parameter data (not aligned)
# ...
# char[] char_data_CPC           // Last  char parameter data (not aligned)
""" % (self.__class__.__name__, self.magic_word)

    def decode(self, msg):
        return self.EwDecodedMessage(self, msg)

    class EwDecodedMessage(object):

        __slots__ = (
            'm',              # Enclosing EwBinaryMessage object
            'total_length',   # Total length of whole message
            'op_code',        # Op code integer value
            'options',        # Option bits as integer
            'request_id',     # Request ID integer value
            'int_args',       # List of int argument values integers
            'char_args'       # List of char argument values as strings
        )

        def __init__(self, m, msg):
            """Private - Initialize an instance from the binary message.

            Parameters:
                m       The containing EwBinaryMessage instance.
                msg     The received binary message as a string (str).

            """
            self.m = m
            pos = [0]

            def get(fmt):
                p = pos[0]
                size = calcsize(fmt)
                result = unpack(fmt, msg[p:p + size])
                pos[0] = p + size
                return result

            try:
                (magic, total_length, self.op_code, options,
                        self.request_id, int_arg_count, char_arg_count) = get(
                        m.endian + '7L')
                if magic != m.magic_number:
                    raise EwMessageError('Invalid magic number: 0x%08x' % magic)
                if len(msg) != total_length:
                    raise EwMessageError(
                        'Message length error, length field: %s, actual: %s'
                        % (total_length, len(msg)))
                self.total_length = total_length
                self.int_args = get(m.endian + str(int_arg_count) + 'L')
                char_arg_sizes = get(m.endian + str(char_arg_count) + 'L')
                self.char_args = get(
                        m.endian + ('%ds' * char_arg_count) % char_arg_sizes)
                if pos[0] != len(msg):
                    raise EwMessageError('Message malformed: pos: %d, len: %d' % \
                                         pos[0], len(msg))
                self.options = m.options_factory.from_int(options)
            except struct_error, e:
                raise EwMessageError('Message malformed: %s' % e)

        def __repr__(self):
            return ('EwMessage(op_code=%r, options=%r, request_id=%r,'
                    ' int_args=%r, char_args=%r)' %
                    (self.op_code, self.options,
                        self.request_id, self.int_args, self.char_args))

        def __str__(self):
            return ('(%s, %s, %s, %s, %s)' %
                    (self.op_code, self.options,
                        self.request_id, self.int_args, self.char_args))

    def read_from_stream(self, stream, method='read'):
        """Reads a message from a file stream.

        Parameters:
            stream  The object representing the stream. Must contain a
                    method "read(byte_count)" that returns a string (str)
                    of no more than "byte_count" bytes read from the stream.
                    The methods name is "read" by default, but an alternate
                    method name can be provided via the "method" parameter.
            method  The method name to use to read data from the stream
                    (default: "read")

        Returns:  An EwDecodedMessage object representing the data read
                  from the stream.

        """
        read = getattr(stream, method)
        header = read(self.header_length)
        if not header:
            # End of file.
            return None
        magic, total_length = unpack(self.header_format, header)
        if magic != self.magic_number:
            raise EwMessageError('Invalid magic number: 0x%08x' % magic)
        return self.EwDecodedMessage(self, header +
                read(total_length - self.header_length))

    def encode(self, op_code, options=0, request_id=0, int_args=(),
            char_args=()):
        """Encode a message.

        Parameters:
            op_code       Op code integer value
            options       Option bits as integer (default: 0)
            request_id    Request ID integer value (default: 0)
            int_args      Sequence of int argument values integers
                          (default: no args)
            char_args     Sequence of char argument values as strings
                          (default: no args)

        Returns: a string (str) representing the binary message.

        """
        fmt = (self.endian + str(7 + len(int_args) + len(char_args)) + 'L' +
                (('%ds' * len(char_args)) % tuple(len(s) for s in char_args)))
        return pack(fmt, self.magic_number, calcsize(fmt),
                op_code, options, request_id,
                len(int_args), len(char_args),
                *chain(int_args, (len(s) for s in char_args), char_args))


class EwMessageError(Exception):
    """Exception raised if message-related error occurs."""


EwBinaryMessage.Error = EwMessageError


def test(ew_binary_message_instance):
    """Little test program -- exercises an EwBinaryMessage subclass with a few
       test messages.

    Parameters:
        ew_binary_message_instance  An instance to test.

    """
    for message in [
                (100, 0x00000000, 0, [], []),
                (101, 0x0000ffff, 1, [11, 22, 33, 44],
                    ['string1', 'string2']),
                (102, 0x0000aaaa, 2, [], ['string3']),
                (103, 0x00005555, 3, [55], []),
                (104, 0x00000000, 4, [0], ['']),
            ]:

        print
        print 'input:', message
        encoded = ew_binary_message_instance.encode(*message)
        decoded = ew_binary_message_instance.decode(encoded)
        print 'str:', decoded
        print 'repr:', repr(decoded)
        a_name = iter(ew_binary_message_instance.option_bit_values).next()
        print 'Option word: 0x%x' % decoded.options.options_int
        print 'Option %s: %s' % (a_name, getattr(decoded.options, a_name))


if __name__ == '__main__':
    class MyMessage(EwBinaryMessage):
        def __init__(self):
            EwBinaryMessage.__init__(self, option_bit_values={
                'a': 1,
                'b': 2,
                'c': 4,
            })

    test(MyMessage())
