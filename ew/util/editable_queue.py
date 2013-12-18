#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
import Queue
from ew.util import ew_logging as log

logger = log.getLogger('ew.util.editablequeue')

class EditableQueue:
    """Provide a priority queue wrapper that allows filtering items out of
    the queue and simplfies queue interaction"""
    Priority_Immediate, Priority_High, Priority_Normal, Priority_Low = 0,1,5,9
    def __init__(self):
        self. _queue = Queue.PriorityQueue()

    def put(self, item, priority= None):
        if not priority: priority = self.Priority_Normal
        self._queue.put_nowait((priority, item))
        logger.debug('Put %s on queue with priority %d', item, priority)

    def get(self, wait=True, seconds=None):
        return self._queue.get(wait, seconds)[1]

    def remove_all(self, limiting_test = None):
        """removes all elements limited by limiting_test."""
        to_keep = []
        with self._queue.mutex:
            for _ in range(self._queue.qsize()):
                entry = self._queue.get_nowait()
                self._queue.task_done()
                if limiting_test:
                    func,args = entry[1]
                    if not limiting_test(func, args):
                        to_keep.append(entry)
        for stuff in to_keep:
            self._queue.put_nowait(stuff)





