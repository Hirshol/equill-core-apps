#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
import sys, re
from cStringIO import StringIO
from itertools import chain

class DsApiUtil(object):

    magic_number = 0x131C014E

    endian = '@'

    verbose = False

    def __init__(self, indent=0):
        """
        Parameters"
          indent -- Number of spaces to indent all output lines.
        """
        self.indent = ' ' * indent

    def generate_method_text(self, name, opcode, options, parameters,
            docstring=None, out_file=sys.stdout, verbose=False):
        """Generate method definition text from given specification.
        Parameters:
          name -- method name
          opcode -- op code integer
          options -- iterable of option names
          parameters -- iterable of parameter names. Type is specified by suffix
            of ":i" => integer, ":s" => string. Default if no suffix is integer.
          docstring -- doc string of generated method. If omitted, a string
            is computed from the method name.
          out_file -- file to output generated method text -- default stdout.
          verbose -- additional diagnostic output (maybe) to stderr
        """
        if not (name and opcode and options is not None and
                parameters is not None):
            raise ValueError("Not all required arguments provided -"
                    " name=%r, opcode=%r, options=%r, parameters=%r" %
                    (name, opcode, options, parameters))
        if not docstring:
            docstring = name[0].upper() + name[1:].replace('_', ' ') + '.'

        # Compute the options value expression.
        opt_params = []
        if not options:
            opt_expr = '0'
        else:
            opt_expr = []
            for opt in options:
                opt_expr.append("(0x%02x if %s else 0)" % (
                        self._option_masks[opt], opt))
                opt_params.append(opt)
            opt_expr = '(' + " |\n                    ".join(opt_expr) + ')'

        # From parameters, compute Python struct.pack() format string and
        # arguments.
        param_names = []
        string_params = []
        int_params = []
        for param in parameters:
            param_split = param.split(':')
            if len(param_split) == 2:
                param_name, param_type = param_split
            else:
                param_name, = param_split
                param_type = 'i'
            param_names.append(param_name)
            (string_params if param_type == 's' else int_params).append(
                    param_name)
        fmt_args_counts = [len(int_params), len(string_params)]
        #fmt_args_ints = int_params
        #fmt_args_strings = chain(("len(%s)" % param for param in string_params),
        #        string_params)
        #fmt_args_1 = [len(int_params)] + int_params
        #fmt_args_2 = ([len(string_params)] +
        #        ["len(%s)" % param for param in string_params])
        fmt = (("%s%sL" % (self.endian, 7 + len(parameters))) +
                ('%ds' * len(string_params)))
        #fmt_args_2.extend(string_params)
        opt_names = [x + '=False' for x in opt_params]
        function_params = (['self'] + param_names + opt_names +
                ['request_id=0'] + ['wait=False'])
        function_params = (
                (", " if len(function_params) <= 3 else ",\n        ").
                join(function_params))

        pack_args_ops = ', '.join([str(opcode), opt_expr])
        pack_args_counts = ', '.join(str(x) for x in fmt_args_counts)
        #pack_args_1 = ', '.join([str(x) for x in fmt_args_1])
        #fmt = ''.join(fmt)

        def print_indent(s):
            self.print_indent(out_file, s)

        print >>out_file
        print_indent('''\
def %s(%s):
    """%s (opcode: %s)"""
    if wait:
        request_id, event = prewait('%s')
''' % (name, function_params, docstring, opcode, name))

        # Output format string.
        if not string_params:
            # Format with no string params.
            print_indent('''\
    fmt = %r
''' % (fmt))

        elif len(string_params) == 1:
            # Format with just one string parameter.
            print_indent('''\
    fmt = %r %% len(%s)
''' % (fmt, string_params[0]))

        else:
            # Format with more than one string param.
            print_indent('''\
    fmt = %r %% (
            tuple(len(arg) for arg in (
                %s)))
''' % (fmt, ', '.join(string_params)))

        # Output "pack" call.
        print_indent('''\
    self._send(pack(fmt, 0x%08X, calcsize(fmt),
            # Op code and options
            %s,
            request_id,
            # Int and char arg counts
''' % (self.magic_number, pack_args_ops))

        if int_params:
            if string_params:
                # Int and string args.
                print_indent('''\
            %s,
            # Int args
            %s,
            # String arg lengths
            %s,
            # String args
            %s))
''' % (pack_args_counts, ', '.join(int_params),
        ', '.join("len(%s)" % x for x in string_params),
        ', '.join(string_params)))
            else:
                # Int args only.
                print_indent('''\
            %s,
            # Int args
            %s))
''' % (pack_args_counts, ', '.join(int_params)))
        else:
            if string_params:
                # String args only.
                print_indent('''\
            %s,
            # String arg lengths
            %s,
            # String args
            %s))
''' % (pack_args_counts,
        ', '.join("len(%s)" % x for x in string_params),
        ', '.join(string_params)))
            else:
                # No args.
                print_indent('''\
            %s))
''' % (pack_args_counts))

        print_indent('''\
    if wait:
        return postwait('%s', request_id, event)

%s.opcode = %s
''' % (name, name, opcode))


    _option_masks = {
        # Listed alphabetically.
        'clear_ink':         16,
        'delete_image':       8,
        'disable_page_turn': 32,
        'flash':              2,
        'force_reload':       1,
        'redraw':             4,
    }


    def print_indent(self, out_file, s):
        if hasattr(sys.modules[__name__], 'wrap_line'):
            if True:
                # Using nested iterators.
                print >>out_file, "\n".join((self.indent + line).rstrip()
                    for line in chain.from_iterable(wrap_line(
                            orig_line, 79 - len(self.indent))
                        for orig_line in s.rstrip().split("\n")))
            else:
                # Using loop.
                lines = []
                for orig_line in s.rstrip().split("\n"):
                    for line in wrap_line(orig_line, 79 - len(self.indent)):
                        lines.append((self.indent + line).rstrip())
                print >>out_file, "\n".join(lines)
        else:
            print >>out_file, \
                "\n".join(
                    [(self.indent + line).rstrip()
                        for line in s.rstrip().split("\n")])


    def make_method(self, global_dict, *args, **kwargs):
        """Return a defined method from given specifications.
        Parameters:
          global_dict -- the global environment of the caller
            (usually globals())
          args, kwargs -- arguments to pass to "generate_method_text".
        """
        verbose = self.verbose or bool(kwargs.get('verbose'))
        name = args[0] if args else kwargs['name']
        local_dict = {}
        io = StringIO()
        kwargs.update([('out_file', io)])
        self.generate_method_text(*args, **kwargs)
        method_str = io.getvalue()
        io.close()
        exec method_str in global_dict, local_dict
        if verbose:
            print '### method:', method_str
            print '### end method'
        func = local_dict[name]
        func.name = name
        return func

    #
    # Generates a series of unit test for a function.
    # Returns count of unit tests generated.
    #
    def generate_unit_test_set(self, name, opcode, options, parameters,
            docstring=None, out_file=sys.stdout, verbose=False):
        """Generate text of a series of unit test methods from given
           specification.
        Parameters:
          name -- method name
          opcode -- op code integer
          options -- iterable of option names
          parameters -- iterable of parameter names. Type is specified by suffix
            of ":i" => integer, ":s" => string. Default if no suffix is integer.
          docstring -- doc string of generated method. If omitted, a string
            is computed from the method name.
          out_file -- file to output generated method text -- default stdout.
          verbose -- additional diagnostic output (maybe) to stderr
        """
        if not docstring:
            docstring = name[0].upper() + name[1:].replace('_', ' ') + '.'
        if verbose:
           print >>sys.stderr, ("name:', %r, opcode:', %r,"
                    " options:', %r, parameters:', %r, docstring:', %r" % (
                        name, opcode, options, parameters, docstring))
        if not (name and opcode and options is not None and
                parameters is not None):
            raise ValueError("Not all required arguments provided -"
                    " name=%r, opcode=%r, options=%r, parameters=%r" %
                    (name, opcode, options, parameters))

        def print_indent(s):
            self.print_indent(out_file, s)

        print_indent('''\

# ===============================================================

# Test set for %r
#   Parameters: %s
#   Options: %s

''' % (name, ', '.join(parameters) if parameters else "none",
            ', '.join(options) if options else "none"))
        params = parameters
        self.gen_unit_test(name, opcode, options, params, True, None, False)
        self.gen_unit_test(name, opcode, options, params, False, 1234, False)
        self.gen_unit_test(name, opcode, options, params, False, None, True)
        return 3  # Returns count of unit tests generated.

    #
    # Generates a single unit test for a function.
    #
    def gen_unit_test(self, name, opcode, options, parameters, defaults,
            request_id,
            wait, out_file=sys.stdout, verbose=False):
        """Generate text of a unit test method from given specification.
        Parameters:
          name -- method name
          opcode -- op code integer
          options -- iterable of option names
          parameters -- iterable of parameter names. Type is specified by suffix
            of ":i" => integer, ":s" => string. Default if no suffix is integer.
          defaults -- if true, generate method exercising default values,
            otherwise supply values for all parameters.
          request_id -- The request ID integer if any, None means no request ID.
          wait -- if true, generates a method exercising the wait option
          out_file -- file to output generated method text -- default stdout.
          verbose -- additional diagnostic output (maybe) to stderr
        """

        def print_indent(s):
            self.print_indent(out_file, s)

        print_indent('''\

def test_%s_%s%s(self):
    if verbose:
        print '\\n%s %s%s'
    %s
    try:
        ds.%s(
''' % (name, "defaults" if defaults else "nondefault",
    "_w_wait" if wait else "", name, "defaults" if defaults else "non-default",
    " & wait" if wait else "", "notify_later()" if wait else "", name))
        int_params = []
        string_params = []
        param_number = 0
        for param in parameters:
            param_split = param.split(':')
            if len(param_split) == 2:
                param_name, param_type = param_split
            else:
                param_name, = param_split
                param_type = 'i'
            param_number += 1
            #print '@@@ param: %r, split: %r, name: %r, type: %r' % (
            #    param, param_split, param_name, param_type)
            if param_type == 's':
                param_value = str(param_number)
                string_params.append(param_value)
            else:
                param_value = param_number
                int_params.append(param_value)
            print_indent('''\
                %r,
''' % param_value)
        opt_bits = 0
        for opt in options:
            opt_bits |= self._option_masks[opt]
            print_indent('''\
                %s,
''' % ("# %s=False" if defaults else "%s=True") % opt)
        if request_id:
            print_indent('''\
                request_id=%r,
''' % request_id)
        if wait:
            print_indent('''\
                wait=True,
''')
        print_indent('''\
        )
    except DsMessageError, e:
        self.fail('Decoding exception: %s' % e)
''')
        if wait:
            print_indent('''\
    message = notify_check()
    self.assertFalse(message, message)
''')
        print_indent('''\
    self.assertEqual(send_data.op_code, %s)
    self.assertEqual(send_data.options, %s)
    self.assert%sEqual(send_data.request_id, %s)
    self.assertEqual(send_data.int_args, %s)
    self.assertEqual(send_data.char_args, %s)
''' % (opcode, "0x00000000" if defaults else "0x%08x" % opt_bits,
    "Not" if wait else "", request_id if request_id else 0,
    tuple(int_params), tuple(string_params)))


#
# Wraps long lines to a specified length. Not completely general for
# wrapping program source code, but works OK for this application.
#       - Continued lines are indented by 8 spaces.
#       - Properly breaks comment lines.
# Shortcoming:
#       - Wraps on space-separated words, so could be troublesome of a
#           string literal containing spaces is broken.
#
def wrap_line(line, width=79, comment_regex =r'\#'):
    if len(line) <= width:
        return [line]
    m = re.match(r'( *)(' + comment_regex + r')?', line)
    next_indent = m.group(1)
    next_prefix = (m.group(2) or "") + "        "
    indent = prefix = ""
    next_width = width - (len(next_prefix) + len(next_indent))
    seg_pat = re.compile(r'(.*) +[^ ]*$')
    lines = []
    while len(line) > width:
        seg = line[:width]
        if len(seg) >= width:
            m = seg_pat.match(seg)
            if m:
                seg = m.group(1)
            lines.append((indent + prefix + seg).rstrip())
            line = line[len(seg):].lstrip()
            indent = next_indent
            prefix = next_prefix
            width = next_width
    if line:
        lines.append((indent + prefix + line).rstrip())
    return lines
