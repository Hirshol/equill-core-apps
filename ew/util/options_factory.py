#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
class BinaryOptions:
    """Simple binary options class"""
    def __init__(self, **options):
        self._options = options

    def to_integer(self, **args):
        result = 0
        for k,v in args.iteritems():
            if v:
                opt_bit = self.options.get(k, 0)
                result |= opt_bit
        return result

    def from_integer(self, integer):
        result = {}
        for k,v in self._option.iteritems():
            result[k] = bool(integer & v)
        return result



"""
A class to facilitate easy handling of binary options stored as bits in
an integer value.
  - Access to option values by name as object attributes
  - Access to the option bits integer
  - Construction of new objects from either their integer value or by
    specifying option names
  - String representations showing option names
  - Comparable, hashable
"""

class OptionsFactory(object):
    """
    A class to facilitate easy handling of binary options stored as bits in
    an integer value.
    """

    __slots__ = 'factory_name', 'option_bit_values',

    def __init__(self, factory_name=None, **option_bit_values):
        """Initializes an OptionsFactory.
        "option_bit_values" is a mapping of option names to their bit mask
          values.
          E.g. OptionsFactory(a=1, b=2, c=4)
        """
        self.factory_name = factory_name
        self.option_bit_values = option_bit_values
        self._set_up_options_class()

    def from_int(self, options_int):
        """Create an Options object from the value of an option bits integer.
        E.g. factory.from_int(0x5)
        """
        return self.Options(options_int)

    def from_true_option_names(self, names):
        """Create an Options object from the names of true options.
        "names" is an iterable of option names that are to have a "true" value.
        Option names not in the sequence will have a "false" value.
        E.g. factory.from_true_option_names(['a', 'c'])
        """
        return self.Options(self.int_from_true_option_names(names))

    def int_from_true_option_names(self, names):
        """Create the int flags value from the names of true options.
        "names" is an iterable of option names that are to have a "true" value.
        Option names not in the sequence will have a "false" value.
        E.g. factory.int_from_true_option_names(['a', 'c'])
        """
        options_int = 0
        try:
            for name in names:
                options_int += self.option_bit_values[name]
        except KeyError:
            raise ValueError('Unknown option name: %r' % name)
        return options_int

    def from_keyword_args(self, **kwargs):
        """Create an Options object from keyword arguments.
        The arguments have option names as keywords with associated boolean
        values. Options not specified will have a "false" value.
        E.g. factory.from_keyword_args(a=True, c=True)
        """
        return self.Options(self.int_from_keyword_args(**kwargs))

    def int_from_keyword_args(self, **kwargs):
        """Return the int flags value from keyword arguments.
        The arguments have option names as keywords with associated boolean
        values. Options not specified will have a "false" value.
        E.g. factory.int_from_keyword_args(a=True, c=True)
        """
        options_int = 0
        try:
            for name, value in kwargs.iteritems():
                if value:
                    options_int += self.option_bit_values[name]
        except KeyError:
            raise ValueError('Unknown option name: %r' % name)
        return options_int

    class Options(object):
            """Class to represent option bit values.
            Option fields (bits) are accessed as properties.
            E.g.:
                >>> options.a  # Value of 'a' option
                True
            """

            __slots__ = 'options_int',

            def __init__(self, options_int):
                """Initializes an Options instance."""
                self.options_int = options_int

            def true_option_names(self):
                """Return the names of options that are true."""
                options_int = self.options_int
                true = []
                for name, bit_value in sorted(
                        self.factory.option_bit_values.iteritems()):
                    if options_int & bit_value:
                        true.append(name)
                return true

            def __repr__(self):
                """Returns a source code type representation of this object.
                E.g. => Options(a=True, c=True)
                """
                #if not self.options_int:
                #    return "Options()"
                #return "Options(%s=True)" % "=True, ".join(
                #        self.true_option_names())
                options_int = self.options_int
                return 'Options(%s)' % (", ".join("%s=%s" % (name, bool(options_int & bit_value))
                        for name, bit_value in sorted(
                        self.factory.option_bit_values.iteritems())))

            def __str__(self):
                """Returns a succinct string representation of this object.
                E.g. => {a, c}
                """
                return '{%s}' % ', '.join(self.true_option_names())

            def __cmp__(self, other):
                """Compare
                If other is an integer, the comparison is between this object's
                options_int and other.
                If other is an instance of this class, the comparison is
                between this object's options_int and other.options_int.
                """
                if isinstance(other, int):
                    return cmp(self.options_int, other)
                if isinstance(other, self.__class__):
                    return cmp(self.options_int, other.options_int)
                return cmp(self, other)

            def __hash__(self):
                return hash(self.options_int)

    def _set_up_options_class(self):
        """Private - Perform some setup of the embedded Options class
           based on factory parameters."""
        # Add option properties to Options class.
        for name, value in self.option_bit_values.iteritems():
            def make_getter(value):
                def f(self):
                    return bool(self.options_int & value)
                return f
            f = make_getter(value)
            f.__name__ = name
            setattr(self.Options, name, property(f, doc="Get %s option" % name))
        # Make a class variable pointing to this factory instance.
        self.Options.factory = self

    def __repr__(self):
        if self.factory_name:
            return 'OptionsFactory(%r, %r)' % (self.factory_name,
                    sorted(self.option_bit_values.iteritems()))
        else:
            return 'OptionsFactory(%r)' % (
                    sorted(self.option_bit_values.iteritems()))

if __name__ == '__main__':
    factory = OptionsFactory('protocol_x', a=1, b=2, c=4)
    print 'factory ("protocol_x", a=1, b=2, c=4):\n    ', factory
    opts = factory.from_int(0x5)
    print 'from_int 0x5 (as str):', opts
    print 'from_int 0x5 (as repr):', repr(opts)
    print 'from_true_option_names ["a", "c"]:', \
            factory.from_true_option_names(['a', 'c'])
    print 'int_from_true_option_names ["a", "c"]:', \
            factory.int_from_true_option_names(['a', 'c'])
    print 'from_keyword_args: a=True, c=True, b=False', \
            factory.from_keyword_args(a=True, c=True, b=False)
    print 'int_from_keyword_args a=True, c=True, b=False:', \
            factory.int_from_keyword_args(a=True, c=True, b=False)
    print 'opts.a 0x5:', opts.a
    print 'opts.b 0x5:', opts.b
