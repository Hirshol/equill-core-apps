#!/usr/bin/env python
from __future__ import with_statement

import time, os, sys, imp, errno, fnmatch


def any_satisfying(test, iterable):
    """returns the first element in the iterable sequence that satisfies the test function or None"""
    for x in iterable:
        if test(x):
            return x
    return None

def if_any(func, sequence):
    """returns whether anything in the sequence satisfies the test func"""
    for x in sequence:
        if func(x):
            return True
    return False

def standard_date(epochtime):
    """returns the YYYY/mm/dd time string from a float epoch time"""
    return time.strftime('%Y/%m/%d', time.localtime(epochtime))

def short_date_time(epochtime=None):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(epochtime))

def standard_date_time(epochtime=None):
    return time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(epochtime))

def standard_doc_path(doc_id, subdir='inbox'):
    """builds and returns a standard document or template path from the doc_id.  The subdir argument defaulst to inbox. Use
    'templates' for a template path"""
    import system_config
    return os.path.join(system_config.data_home, subdir,
                        doc_id + '.memphis')


def docid_from_path(a_path):
    """return the standard docid from the specified memphis document path"""
    return os.path.basename(a_path).split('.memphis')[0]

#lifted from somewhere online. A generator for files under the given root that match the given pattern
def locate(pattern, root=os.getcwd()):
    """generator yielding files under the given root that satisfy the given pattern"""
    for path, dirs, files in os.walk(root):
        for filename in [os.path.abspath(os.path.join(path, filename)) for filename in files if fnmatch.fnmatch(filename, pattern)]:
            yield filename

def document_class_at_path(path):
    from sdk.document import Document

    apath = path.split('memphis.document.d')[0]
    code_path = os.path.join(apath, 'memphis.document.d', 'code',
                             'dec.py')
    if not os.path.isfile(code_path): return None

    def code_module():
        import imp
        mod = None
        mod_path = os.path.dirname(code_path)
        add_path = not mod_path in sys.path
        if add_path:
            sys.path.append(mod_path)
        print '>>>>>>>code_path is %s' % code_path
        with open(code_path, 'r') as dec_file:
            mod = imp.load_module('_dec', dec_file,
                                  os.path.basename(code_path),
                                  ('.py', 'r', imp.PY_SOURCE))
        if add_path:
            sys.path.remove(mod_path)
        return mod


    def code_module2():
        #os.chdir(os.path.dirname(code_path))
        sys.path.append(os.path.dirname(code_path))
        print 'sys.path:', sys.path
        return __import__('dec', globals(), locals(), [], -1)

    def doc_class():
        dec_class = None
        code = code_module2()
        if(code):
            mod_dict = code.__dict__

            def is_strict_subclass(x,y):
                return (x != y) and issubclass(x,y)

            classes = [v for v in mod_dict.values() if isinstance(v,type)]
            print "\n"

            for c in classes:
                print '%s%s is subclass of Document = %s' % (c.__name__, tuple(c.__bases__), issubclass(c, Document))

            candidates = [v for v in classes if \
                              issubclass(v, Document)]

            print 'candidates = %s'%  candidates

            if candidates:
                if len(candidates) > 1:
                    candidates = filter(lambda x: \
                                            not if_any(
                            lambda y: is_strict_subclass(y,x),
                            candidates), candidates)

                dec_class = candidates[0]
        else:
            print 'no module found at %s' % path

        return dec_class
    return doc_class()

def document_at_path(path):

    the_class = document_class_at_path(path)
    print 'opening class %s' % the_class
    return the_class(path) if the_class else None

def get_document_lock(docid, name, exclusive, non_blocking=False, explicit_path=None,
                      subdir='inbox'):
    """Return an ExclusiveLock or SharedLock object for the specified
        lock name.
    Parameters:
      name -- The lock name as a string, e.g. 'loaded', 'document',
        'status', ...
      exclusive -- If true returns an exclusive lock, otherwise a shared
        lock
      non_blocking -- If true, the lock object has non_blocking=True
    """
    import lock
    path = explicit_path if explicit_path else standard_doc_path(docid, subdir)
    if not os.path.isdir(path):
        raise Exception('%s is not a valid document id' % docid)
    lock_dir = os.path.join(path, "local/memphis-locks")
    try:
        os.makedirs(lock_dir)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise
    return (lock.ExclusiveLock if exclusive else lock.SharedLock)(
            os.path.join(lock_dir, name + '.lock'), non_blocking)

def exclusive_document_lock(docid, lockname, wait=True, explicit_path=None, subdir='inbox'):
    return get_document_lock(docid, lockname, exclusive=True,
                             non_blocking=(not wait), subdir=subdir,
                             explicit_path=explicit_path)

def shared_document_lock(docid, lockname, wait=True, explicit_path=None, subdir='inbox'):
    return get_document_lock(docid, lockname, exclusive=False,
                             non_blocking=(not wait), subdir=subdir,
                             explicit_path=explicit_path)


