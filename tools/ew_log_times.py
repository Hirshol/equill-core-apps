# Copyright 2011 Ricoh Innovations, Inc.
"""Operations on time field of EW logs."""

import re

class EwLogTimes(object):
    """Operations on time field of EW logs."""

    _date_pat = re.compile(
        r'(20\d{2})\-(\d{2})\-(\d{2}) (\d{2}):(\d{2}):(\d{2})[\.\,](\d{3})\:? ')

    @classmethod
    def is_dated_line(cls, line):
        """Return whether line is a dated log line."""
        return bool(cls._date_pat.match(line))

    @classmethod
    def time_value(cls, line):
        """
        If line is not a dated log line, return None, otherwise return an integer which is
        monotonically increasing with successive dates.
        """
        m = cls._date_pat.match(line)
        if not m:
            return None
        return cls.compute_time_value(*[int(x) for x in m.group(
                1, 2, 3, 4, 5, 6, 7)])

    @staticmethod
    def compute_time_value(yr, mo, da, hr, mi, se, ms):
        """
        Compute a time value from a date.
        Returns an integer which is monotonically increasing with
        successive dates.
        """
        return (((((yr * 12 + mo) * 31 + da) * 24 + hr) * 60 +
                mi) * 61 + se) * 1000 + ms

    @classmethod
    def large_time_value(cls):
        """
        Return a time value larger than any value calculated from a
        date expected to be seen in the viewed logs.
        """
        return cls._large_time_value

EwLogTimes._large_time_value = EwLogTimes.compute_time_value(
        3000, 0, 0, 0, 0, 0, 0)
