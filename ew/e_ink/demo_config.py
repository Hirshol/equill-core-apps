#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.
"""
Information about demo for demo_switcher.

To make the demo_switcher recognize a demo, create a 'demo_menu.py'
file for your demo: ~guest/*/demo_menu.py or ~guest/*/bin/demo_menu.py.

Here is a simple example::

    import pyedo

    demos = [
        pyedo.DemoConfig(
            text='Brazil/Odessa',
            tmp_links={'options_default.py':'options.py'},
            pid_file_list=['/tmp/demo_with_laptop.py.pid',
                           '/tmp/widget_manager.py.pid'],
            start_script='demo_start.sh',
            stop_script='demo_stop.sh',
            stop_pentrack=True),
    ]

More that one pyedo.DemoConfig can be used to define more
than one menu item. Menu items can be created dynamically::

    import pyedo
    import glob
    import os.path

    demos = []
    for i in glob.glob('/mnt/sd/*.edo'):
        demos.append(pyedo.DemoConfig(
            text=os.path.basename(i)[:-4],
        ))

The demo switcher will keep running and watch the EDO's orientation
use accelerometers while running. When the EDO is inverted, it will
read the accelerometers at high speed to detect shaking.  Your
demo/application must not use too much CPU when the EDO is inverted
(eink screen down, camera up) for shake detection to work. The Demo
Switcher will run scripts to pause and continue your demo/application
if you provide them. Scripts can send STOP and CONT signals or use
signals such as USR1 and USR2 to request pausing and continuing or do
something else. A future version of the Demo Switcher might turn off
force buttons, etc. while the edo is inverted.

 - $Id$
 - $HeadURL$
"""

import os.path
import signal
import shutil
import os
import subprocess
import time

def process_exists(pid):
    """Return True is pid matches an existing, non-Zombie process."""
    if not pid:
        return None
    pid = int(pid)
    if not os.path.exists('/proc/%d' % pid):
        return False
    fname = '/proc/%d/status' % pid
    if not os.path.exists(fname):
        return False
    try: # handle process termination race condition
        lst = open(fname).readlines()
    except IOError:
        lst = []
    for i in lst:
        if i.startswith('State:'):
            a = i.split()
            if (len(a) >= 2) and (a[1] == 'Z'): # zombie
                return False
    return True

def get_abs_dir(path):
    """
    Return absolute directory name for path.
    """
    return os.path.abspath(os.path.dirname(path))

def get_tmp_path(fname=None, **opts):
    """
    Return path in temporary directory for fname or return temporary
    directory if fname is None. The temporary directory will be
    created if it does not exist.

    opts::
      tmp_dir='/tmp/demo_switcher'
    """
    base = opts.get('tmp_dir', '/tmp/demo_switcher')
    if not os.path.isdir(base):
        os.mkdir(base)
    if fname:
        return os.path.join(base, fname)
    else:
        return base

def fs_is_rw(mount='/'):
    """
    Is a file system read/write?
    """
    lines = open('/proc/mounts').readlines()
    for i in lines:
        a = i.split()
        # / is tricky, want the ext3 filesystem, not rootfs
        if (len(a) > 3) and (a[1] == mount) and (a[2] in ['ext2', 'ext3']):
            options = a[3].split(',')
            if 'rw' in options:
                return True
            if 'ro' in options:
                return False
    return None

def find_child_processes(pid):
    """
    For a given PID, find it's child processes by searching /proc.
    This is not recursize, so it only finds immediate children.
    """
    s_pid = str(pid)
    children = []
    for i in os.listdir('/proc'):
        if not i.isdigit():
            continue
        path = os.path.join('/proc', i, 'stat')
        try:
            a = open(path).read().split()
        except IOError, msg:
            # handle race condition of file going away
            continue
        if len(a) < 3:
            continue
        if a[3] == s_pid: # compare parent pid
            children.append(i)
    return children

def find_all_child_processes(pid_list):
        """
        Add all child processes of the processes in pid_list
        to pid_list recursively.
        """
        check = pid_list[:] # copy of list
        while check:
            j = check.pop()
            pl = find_child_processes(j)
            for i in pl:
                if not i in pid_list:
                    check.append(i)
                    pid_list.append(i)
        return pid_list

def safe_kill(pid, sig):
    """
    Call os.kill. Normally returns True. Returns False instead 'No
    such process' exception or 'No such file or directory: '/proc/#/status'.
    pid can be int or string convertable to an int.
    """
    rval = True
    try:
        os.kill(int(pid), sig)
    except OSError:
        rval = False
    except IOError:
        rval = False
    return rval

def kill_processes_in_list(pid_list, **opts):
    """
    For each process in pid_list, if it is still running after X seconds,
    kill it. After Y more seconds, if there are still any processes around,
    kill with 'kill -9'.

    opts:
      wait1=25   wait1/10 is X seconds
      wait2=25   wait2/10 is Y seconds
      verbose=True
    """
    verbose = opts.get('verbose')
    if verbose:
        print "kill_processes in list: PIDs", pid_list
    wait1 = opts.get('wait1', 25)
    wait2 = opts.get('wait2', 25)
    for i in range(wait1 + wait2):
        pl = pid_list[:] # copy
        for pid in pl:
            if process_exists(pid):
                if i == (wait1 + wait2 - 1): # only first time
                    rval = safe_kill(pid, signal.SIGTERM)
                    if verbose:
                        if rval:
                            print "kill_all_processes: Kill PID %s" % pid
                        else:
                            print "kill_all_processes: no process w/ PID %s" % pid
                elif i == (wait1 + wait2 - 1):
                    rval = safe_kill(pid, signal.SIGKILL) # kill -9
                    if verbose:
                        if rval:
                            print "kill_all_processes: Kill -9 PID %s" % str(pid)
                        else:
                            print "kill_all_processes: no process w/ PID %s for kill -9" % str(pid)
                else:
                    break
            else:
                pid_list.remove(pid)
        if not pid_list:
            break
        time.sleep(0.1)


class DemoConfig:
    """
    Information about demo for demo_switcher. Each object can create
    one Demo Switcher menu time.

    Notes::
      Handle deleting temporary files?
    """

    def __init__(self, **opts):
        """
        opts for starting/stopping controlling demos::

          start_script=FNAME   script for starting demo
          stop_script=FNAME    script for stopping demo
          pause_script=FNAME
          continue_script=FNAME
          start_args=STRING    arguments passed to start script (can use '&'
                               to run in background)
          environ={}           Set environment variables for start script
          stop_args=STRING     arguments passed to stop script
                               (Using stop_args is not recommended, since
                                the wacom watchdog will call it without
                                these arguments)
          pause_args
          continue_args
          daemon='wacom'       use /etc/init.d/ script
          exit=True            exit the demo switcher (not implemented yet)
          stop_pentrack=False  do not stop pentrack server if False
          ptu_tsscale_min=1    Minimum value for PTU_TSSCALE if not stopping
                                  pentracking (not implemented yet)
          ptu_tsscale_max=16   Maximum value for PTU_TSSCALE if not stopping
                                  pentracking (not implemented yet)
          tmp_links={ 'src1':'dst1', 'src2':True)
                               create symlinks from demo directory
                               to /tmp/demo_switcher, renaming if
                               value is a string and using the
                               same name if value is True.
          tmp_copy={ 'src1':'dst1', 'src2':True)
                               copy files from demo directory
                               to /tmp/demo_switcher, renaming if
                               value is a string and using the
                               same name if value is True.
          pid_file=PATH        filename where PID of process is stored
          pid_file_list=[PATH, ...]
                               list of filenames where PIDs of processes
                               are stored
          stop_pid=True        send signal to PIDs in PID file(s) to stop
          pause_pid=True       send signal to PIDs in PID file(s) to pause
          continue_pid=True    send signal to PIDs in PID file(s) to continue
          background=False     start_script is the demo (instead of start
                               launches demo in background and returns)
          root_rw=True         Make / be read/write when running demo
          home_rw=True         Make /home be read/write when running demo (EDO 1.5 only)
          data_rw=True         Make /data be read/write when running demo (EDO 2.0 only)
          automatic=True       Instead of initially showing the menu, run
                               this demo. (If more than one demo uses
                               automatic=True, only one will run.)

        opts for menu appearance::

          icon='foo.pgm'       icon image for menu
          text='A super demo'  text for menu
          text_size=36         size of text for menu
          enable=False         disable this demo if False
          weight=0             bigger weight --> later menu position
          network=True         only enable if a network connection is present
          network=False        only enable if no network connections are present

        opts typically set by importer instead::

          verbose=True
          file=PATH

            (tmp_dir, eink and status are set by the demo switcher if
             the options for these are not specified or are false
             (e.g. None))

          tmp_dir='/tmp/demo_switcher'
          eink=pyedo.EinkSparkle(None, None)
          status=pyedo.Status()

        Notes::

          Add name, version, date info? Add icons/images?

        """
        self.opts = opts
        self.enable = opts.get('enable', True)

        # find_demos in demo_switcher.py will initialize self.verbose
        # and self.file
        self.verbose = opts.get('verbose')
        # full path of demo directory and demo_menu.py
        self.file = opts.get('file')
        self.tmp_dir = opts.get('tmp_dir')
        self.eink = opts.get('eink')
        self.status = opts.get('status')
        self.stop_script = 'stop.sh'
        self.pause_script = 'pause.sh'
        self.continue_script = 'continue.sh'
        self.pid_from_start = []
        self.pid_file_list = opts.get('pid_file_list', [])
        pid_file = opts.get('pid_file')
        if pid_file:
            self.pid_file_list.append(pid_file)
        for pf in self.pid_file_list:
            if not ((pf.startswith('/tmp/') or pf.startswith('/var/run'))
                     and pf.endswith('.pid')):
                raise Exception('PID file "%s" does not match "/tmp/*.pid'
                                % pf)
        self.pid_dict = {}
        self.background = opts.get('background', True)
        self.weight = opts.get('weight', 0)
        self.paused = False
        self.network_required = opts.get('network')
        self.host_name = None
        self.interfaces = None
        self.root_rw = opts.get('root_rw')
        self.home_rw = opts.get('home_rw')
        self.data_rw = opts.get('data_rw')
        self.root_make_ro = None
        self.home_make_ro = None
        self.data_make_ro = None

        # self.interfaces is a list of tuples [(interface_name,
        # ip_address), (interface_name, ip_address)].  For EDO,
        # interface_name is always 'wlan0' or 'eth0'.

        if self.verbose: print "DemoConfig.__init__", self.opts

    def set_network_info(self, hostname, interfaces):
        """
        Save network info and disable demo if network requirement
        not matched.
        """
        self.host_name = hostname
        self.interfaces = interfaces
        if (self.network_required == True) and not interfaces:
            self.enable = False
            if self.verbose:
                print "DemoConfig.set_network_info: no network, disabling"
        elif  (self.network_required == False) and interfaces:
            self.enable = False
            if self.verbose:
                print "DemoConfig.set_network_info: network exists, disabling"
        elif self.verbose:
            print "DemoConfig.set_network_info: want=%s have=%s" % (
                str(self.network_required), str(not not interfaces))

    def start(self):
        """
        Start a demo. A derived class can customize this. The default
        is to use a /etc/init.d script.
        """
        flag = False
        self.remove_old_pid_files()
        self.make_tmp_links()
        self.copy_to_tmp()
        self.make_script_links()
        self.mount_rw()
        self.start_helper()

    def remove_old_pid_files(self):
        """
        Remove PID files.
        """
        self.pid_dict = {}
        for pf in self.pid_file_list:
            if os.path.exists(pf):
                try:
                    os.unlink(pf)
                except OSError, ex:
                    if self.verbose:
                        print "Warning: unlink(%s)\n%s" % (pf, str(ex))

    def make_script_links(self):
        """
        Make links for start, pause and continue scripts.
        """
        for script_key, fname in [('stop_script', self.stop_script),
                                  ('pause_script', self.pause_script),
                                  ('continue_script', self.continue_script),
                                  ]:
            script = self.opts.get(script_key)
            if script:
                path = self.get_script(script)
                self.switch_link(path, get_tmp_path(fname))

    def mount_rw(self):
        """
        Mount /, /data and/or /home read-write based on self.root_rw, self.data_rw and self.home_rw.
        """
        for rw_flag, path in [(self.root_rw, '/'), (self.data_rw, '/data'), (self.home_rw, '/home')]:
            if rw_flag:
                is_rw = fs_is_rw(path)
                if is_rw == False:
                    cmd = 'mount -o remount,rw,noatime %s' % path
                    if self.verbose:
                        print cmd
                    os.system(cmd)
                    if path == '/':
                        self.root_make_ro = True
                    elif path == '/data':
                        self.data_make_ro = True
                    elif path == '/home':
                        self.home_make_ro = True
                    else:
                        raise Exception('Bad path in mount_rw')
                elif is_rw == None:
                    raise Exception('Mount point %s not found for mount_rw'
                                    % path)
                elif self.verbose: # is_rw == True
                    print "%s is already mounted read-write" % path

    def start_helper(self):
        """
        Start a demo using either a start_script or an init script.
        Called by start().
        """
        self.pid_from_start = []
        start_script = self.opts.get('start_script')
        if start_script:
            cmd = ''
            environ = self.opts.get('environ')
            if environ:
                for k, v in environ.items():
                    cmd = ('%s=%s ' % (k, v)) + cmd
            cmd += self.get_script(start_script)
            args = self.opts.get('start_args')
            if args:
                cmd += ' ' + args
            p = subprocess.Popen(cmd, shell=True)
            pid, status = os.waitpid(p.pid, 0)
            if self.verbose or (status != 0):
                print "start_helper: pid=%d, status=%d" % (pid, status)
            self.pid_from_start = [pid]
            self.pid_from_start += find_child_processes(pid)
            flag = True
        else:
            init_script = self.get_init_script()
            if init_script:
                cmd = "%s start" % init_script
                os.system(cmd)
                flag = True
        if not flag:
            raise Exception("Do not know how to start demo.")

    def stop(self):
        """
        Stop a demo. A derived class can customize this. The default
        is to use a stop.sh script or /etc/init.d script.
        """
        self.add_pids_for_all()
        flag = False
        if self.opts.get('stop_pid'):
            flag = self.send_signal(signal.SIGTERM)
        else:
            stop_script = self.opts.get('stop_script')
            if stop_script:
                stop_script = self.get_script(stop_script)
                cmd = stop_script
                args = self.opts.get('stop_args')
                if args:
                    cmd += ' ' + args
                os.system(cmd)
                if os.path.islink(stop_script):
                    os.unlink(stop_script)
                flag = True
            else:
                init_script = self.get_init_script()
                if init_script:
                    cmd = "%s stop" % init_script
                    os.system(cmd)
                    flag = True
        flag = self.kill_all_processes_started()
        if not self.background:
            flag = True # If not running in background, OK to not stop
        self.after_demo_stopped()
        if not flag:
            raise Exception("Do not know how to stop demo.")

    def after_demo_stopped(self):
        """
        This is run after a demo is stopped including if
        it does not run in the background.
        """
        for flag, path in [(self.root_make_ro, '/'),
                           (self.data_make_ro, '/data'),
                           (self.home_make_ro, '/home')]:
            if flag:
                cmd = 'mount -o remount,ro,noatime %s' % path
                if self.verbose:
                    print cmd
                os.system(cmd)

    def kill_all_processes_started(self):
        """
        For each process started by the demo, if it is still running,
        kill it.  Returns True always. This means kill stopping
        demo was successful. A derived class can redifine this to
        be less agressive and return True or False.
        """
        kill_processes_in_list(self.pid_from_start, verbose=self.verbose)
        return True

    def send_signal(self, sig):
        """
        Send a signal to each process with a PID file.
        """
        flag = self.get_pid_from_files()
        if self.verbose:
            print "SEND SIGNAL %d to %s, return %s" % (
                sig, str(self.pid_dict.values()), str(flag))
        for fname, pid in self.pid_dict.items():
            if process_exists(pid):
                rval = safe_kill(pid, sig)
                if not rval:
                    print "Failed to send signal to process %d" % int(pid)
        return flag

    def pause(self):
        """
        Pause a demo (so it can be restarted). A derived class can
        customize this.
        """
        if self.opts.get('pause_pid'):
            flag = self.send_signal(signal.SIGSTOP)
            return True
        pause_script = self.opts.get('pause_script')
        if pause_script and not self.paused:
            pause_script = self.get_script(pause_script)
            cmd = pause_script
            args = self.opts.get('pause_args')
            if args:
                cmd += ' ' + args
            os.system(cmd)
            self.paused = True
            return True
        return False

    def do_continue(self):
        """
        Continue a demo (so it can be restarted). A derived class can
        customize this.
        """
        if self.opts.get('continue_pid'):
            flag = self.send_signal(signal.SIGCONT)
            return True
        continue_script = self.opts.get('continue_script')
        if continue_script and self.paused:
            continue_script = self.get_script(continue_script)
            cmd = continue_script
            args = self.opts.get('continue_args')
            if args:
                cmd += ' ' + args
            os.system(cmd)
            flag = True
            self.paused = False
            return True
        return False

    def get_script(self, fname):
        """
        Return the path to a script, using the directory with demo_menu.py
        for relative paths.
        """
        if os.path.isabs(fname):
            path = fname
        else:
            path = os.path.join(os.path.dirname(self.file), fname)
        if not os.access(path, os.X_OK):
            raise Exception('%s is not an executable' % path)
        return path

    def get_init_script(self):
        """
        Return the path to a script in /etc/init.d. Return None
        if no script specified (no 'daemon' in opts).
        """
        daemon = self.opts.get('daemon')
        if daemon:
            init_script = '/etc/init.d/' + daemon
            if not os.path.exists(init_script):
                raise Exception('%s does not exists' % init_script)
            return init_script
        return None

    def make_tmp_links(self):
        """
        Create links specified by tmp_links options. Deletes .pyc files
        corresponding to new .py links.
        """
        d = self.opts.get('tmp_links')
        if not d: return
        dst_dir = self.tmp_dir
        if not os.path.isdir(dst_dir):
            raise Exception('tmp_dir "%s" does not exist.' % str(dst_dir))
        src_dir = os.path.dirname(self.file)
        if not os.path.isdir(src_dir):
            raise Exception('src_dir "%s" does not exist.' % str(src_dir))
        for src, dst in d.items():
            if dst == True:
                dst = os.path.basename(src)
            if os.path.isabs(dst):
                pd = dst
            else:
                pd = os.path.join(dst_dir, dst)
            if os.path.isabs(src):
                ps = src
            else:
                ps = os.path.join(src_dir, src)
            self.switch_link(ps, pd)

    def copy_to_tmp(self):
        """
        Copy files specified by tmp_copy options to /tmp.
        """
        d = self.opts.get('tmp_copy')
        if not d: return
        dst_dir = self.tmp_dir
        if not os.path.isdir(dst_dir):
            raise Exception('tmp_dir "%s" does not exist.' % dst_dir)
        src_dir = os.path.dirname(self.file)
        if not os.path.isdir(src_dir):
            raise Exception('src_dir "%s" does not exist.' % src_dir)
        for src, dst in d.items():
            if dst == True:
                dst = os.path.basename(src)
            if os.path.isabs(dst):
                raise Exception('copy_to_tmp: destination path must be relative')
            else:
                pd = os.path.join(dst_dir, dst)
            if os.path.isabs(src):
                ps = src
            else:
                ps = os.path.join(src_dir, src)
            shutil.copy(ps, pd)

    def switch_link(self, src, dst):
        """
        Create or change a symbolic link if necessary.
        If necessary and dst link ends in .py, delete a corresponding .pyc
        file. Mount filesystem RO if necessary.
        """

        if not os.path.exists(src):
            raise Exception('Source for link %s does not exist' % src)
        dst_exists = os.path.exists(dst)
        if dst_exists and os.path.samefile(src, dst):
            if self.verbose:
                print "using %s --> %s" % (src, dst)
            return

        ro_flag = False
        if not os.access(os.path.dirname(dst), os.W_OK):
            # Acually compare dst with mountpoints?
            if os.path.abspath(dst).startswith('/tmp'):
                raise Exception('Cannot write to %s' % os.path.dirname(dst))
            if os.path.abspath(dst).startswith('/home'):
                mount_dir = '/home'
            elif os.path.abspath(dst).startswith('/data'):
                mount_dir = '/data'
            else:
                mount_dir = '/'
            os.system('mount -o remount,rw,noatime %s' % mount_dir )
            ro_flag = True

        if dst_exists:
	    if os.path.islink(dst):
                os.unlink(dst)
            else:
                raise Exception("%s already exists and is not a sym link." %
                                dst)
        os.symlink(src, dst)
        if self.verbose:
            print "ln -s %s %s" % (src, dst)
        if dst.endswith('.py'):
            pyc = dst + 'c' # .pyc
            if os.path.exists(pyc):
                os.unlink(pyc)
                if self.verbose:
                    print 'rm %s' % pyc
        if ro_flag:
            os.system('mount -o remount,ro,noatime %s' % mount_dir)

    def get_pid_from_files(self):
        """
        Poll to see if PIDs have been written for files. If yes,
        read file and store PID. Returns True
        if all PIDs have been saved.
        """
        flag = True
        for pf in self.pid_file_list:
            if self.verbose: print "GET_PID_FROM_FILES", pf
            if self.pid_dict.get(pf):
                continue
            if not os.path.exists(pf):
                if self.verbose: print "PID file %s does not exist." % pf
                flag = False
                continue
            try:
                f = open(pf)
                s = f.read()
                f.close()
                s = s.strip()
                if s:
                    pid = int(s)
                    self.pid_dict[pf] = pid
                    self.add_pids(pid)
                    if self.verbose: print "GET_PID_FROM_FILES", pid
            except Exception, ex:
                flag = False
                if self.verbose:
                    print "Warning for '%s':\n%s" % (pf, str(ex))
        return flag

    def do_processes_exist(self):
        """
        Check if processes with PID files exist. get_pid_from_files
        should be run first.
        """
        for fname, pid in self.pid_dict.items():
            if process_exists(pid):
                return True
        return False

    def add_pids(self, pid):
        """
        Add a pid and pids for any if it's children to self.pid_from_start
        if they are not already on this list. Only add immediate children.
        """
        pid_list = find_child_processes(pid)
        pid_list.append(pid)
        for i in pid_list:
            if not i in self.pid_from_start:
                self.pid_from_start.append(i)

    def add_pids_for_all(self):
        """
        Add children of processes on self.pid_from_start to this list
        recursively.
        """
        find_all_child_processes(self.pid_from_start)

    def fs_is_rw(self, mount='/'):
        """
        Is a file system read/write?
        (Depreciated. Use function instead.)
        """
        return fs_is_rw(mount)

    def processes_done(self):
        """
        Return TRUE if at least one PID file is used, all PID files were
        created and all processes are gone.

        """
        if not self.pid_file_list:
            if self.verbose: print "PROCESSES_DONE: no PID files"
            return False  # no PID files
        if not self.get_pid_from_files():
            if self.verbose: print "PROCESSES_DONE: not all PID files created yet"
            return False   # not all PID files created yet.
        if self.do_processes_exist():
            if self.verbose: print "PROCESSES_DONE: at least one process still running"
            return False   # at least one process still running
        if self.verbose: print "PROCESSES_DONE: True"
        return True

    def before_display_menu(self, list_of_demos):
        """Hook for derived classes"""
        pass

    def before_start(self, list_of_demos):
        """Hook for derived classes"""
        pass

    def before_stop(self, list_of_demos):
        """Hook for derived classes"""
        pass

