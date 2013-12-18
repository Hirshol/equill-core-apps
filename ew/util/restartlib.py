#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.

import os, signal, time, sys
import ConfigParser
from ew.util import ew_logging as log

# ----------------------------------------------------
# Constants
# ----------------------------------------------------
PERFORMACTIONS = True
PERFORMKILL = True
PIDLOC = "/tmp"
EXCEPTLOC = "/tmp/restartexceptions.txt"

CHECK_WAIT = 5                          # time to sleep between pid checks
SHUTDOWN_WAIT = 10                      # time to sleep waiting for all processes to shut down before hard kills begin
SHUTDOWN_RETRY_WAIT = 1                 # time to sleep before retrying hard process kill

STATLIST = "pid,comm,state,ppip,pgrp,session,tty_nr,tpgid,flags,minflt,cminflt,majflt,cmajflt,utime,stime,cutime,cstime,priority,nice,num_threads,itrealvalue,starttime,vsize,rss,rsslim,strtcode,endcode,startstack,kstkesp,kstkeip,signal,blocked,sigignore,sigcatch,wchan,nswap,cnswap,rt_priority,policy,delayacct,guest_time,cguest_stime".split(",")
HZ = float(os.sysconf(os.sysconf_names['SC_CLK_TCK'])) # system translation multiplier between clock ticks and seconds

# ----------------------------------------------------
# Set up delete character list for filtering Linux proc filesystem
# cmdline file contents, filtering all unprintable and whitespace chars up to chr(32)
# ----------------------------------------------------
DELETECHARS = ""
for i in range(32):
    DELETECHARS += chr(i)


# ----------------------------------------------------
# Logger setup
# ----------------------------------------------------

logger = log.getLogger('ew_tablet')
APP = sys.argv[0]

# ----------------------------------------------------
# Utility Functions
# ----------------------------------------------------

def filecontents(path):
    """filecontents(path) simply opens a file, reads the entire contents, and closes it once again.
    """
    f=open(path,"r")
    content = f.read()
    f.close()
    return content

def removehidden(str):
    """removehidden(str) removes non-printing characters from a a string."""
    global DELETECHARS
    return str.translate(None,DELETECHARS)

def checkprocess(pid, targetcommand):
    """checkprocess(procid,targetcommand) takes an integer process ID and checks the /proc
    file system entries to make sure that the running process was started using the command
    specified by the targetcommand argument. If the process running with the specified ID
    was run by the proper command, we assume that it is still running and needs no restart.
    """
    procfspath = os.path.join("/proc",str(pid))
    if os.path.exists(procfspath):
        cmdlinepath = os.path.join(procfspath,"cmdline")
        cmd = removehidden(filecontents(cmdlinepath))
        if cmd.startswith(targetcommand):
            #print "%s okay" % procid
            return int(pid)
        logger.error("%s does not appear to have the correct command '%s'\n but instead was started with '%s'" % (pid,targetcommand,cmd))
    else:
        logger.error("%s (%s) does not appear to exist as a process" % (pid, targetcommand))
    return False

def testproc(pid):
    """testproc(procid) checks the proc fs for the existence of a given process id."""
    procfspath = os.path.join("/proc",str(pid))
    return os.path.exists(procfspath)    
    
def statprocess(pid):
    """statprocess(procid) obtains the contents of the stat file form the proc file system for the
    given process ID, creating a dictionary of key-value pairs for the contents. See man proc(5)
    for detailed information on the contents of this file."""
    statdict = {}
    procfspath = os.path.join("/proc",str(pid))
    if os.path.exists(procfspath):
        statpath = os.path.join(procfspath,"stat")
        statstr = filecontents(statpath) 
        statarray = statstr.split()
        for i in range(len(STATLIST)):
            statdict[STATLIST[i]] = statarray[i]
    return statdict
    
def procid(pidname, shouldlog=True):

    """procid(pidname) returns the process id for a given pid file path (pidname)
    by reading the contents of the named pid file and returning it, otherwise
    returning false."""

    if os.path.exists(pidname):
        proc = filecontents(pidname)
        if proc:
            pid = proc.split()[0]
            return int(pid.strip())
        else:
            if shouldlog:
                logger.error("pidfile %s appears to be empty" % (pidname))
            return False
    else:
        if shouldlog:
            logger.error("pidfile %s does not exist" % (pidname))
        return False

            

def checkpid(pidname, cmdname):

    """checkpid(pidname, cmdname) reads the contents of the specified pid file, and
    assumes that the contents begin with the integer process identifier of the
    running process. It then calls checkprocess to test that the process with that
    id is in fact the correct process, and if so returns the process ID for use.
    Otherwise it returns False.  """

    p = procid(pidname, shouldlog = False)
    if p:
            return checkprocess(p,cmdname)
    else:
        return False
        
def writepid(processname):
    """writepid(processname) is a utility function to obtain the current process id and
    write it to an appropriate pid file location.
    """
    pid = os.getpid()
    f=open(os.path.join(PIDLOC, processname+".pid"),"w")
    f.write(str(pid))
    f.close()
   
def compareentries(first,second):
    """compareentries(first,second) is a comparison function for use with the sorted() built in function, to sort a set
    of servers needing restart into an appropriate restart order."""
    logger.info("%s(%s) vs %s(%s)" % (first.dict["name"], first.dict["restartlist"], second.dict["name"], second.dict["restartlist"]))
    if second.dict["name"] in first.dict["restartlist"]:
        #logger.info("%s < %s" % (first.dict["name"], second.dict["name"]))
        return -1
    elif first.dict["name"] in second.dict["restartlist"]:
        #logger.info("%s > %s" % (first.dict["name"], second.dict["name"]))
        return 1
    else:
        #logger.info("%s = %s" % (first.dict["name"], second.dict["name"]))
        return 0

def heavyweightcheck(testprogramname):
    """heavyweightcheck(testprogramname) initiates a slow but thoough check for whether a program
    is running, by listing the oprocesses and using grep to count how many times the program
    name appears in the resulting output. Used by the main and secondary restart daemons
    to check for copies of themselves, alllowing them to shut down rahter than starting endless
    copies of themselves.
    """
    psfile = os.popen("ps ax | grep %s | grep -v grep | wc -l" % testprogramname)
    contents = psfile.read()
    psfile.close()
    return int(contents) > 1
        
# ----------------------------------------------------
# Pid Checker
# ----------------------------------------------------

class PidEntry:
    """Class PidEntry is a simple wrapper class which holds a parameter dictionary for each
    server, because ordinary Python dicts are not hashable and therefore not sortable"""
    def __init__(self,dict):
        """standard init method"""
        self.dict = dict
    
    def __repr__(self):
        """standard repr method"""
        return self.dict["name"]
    
    def __lt__(self,other):
        return other.dict["name"] in self.dict["restartlist"] 

class PidChecker:
    """ Class PidChecker reads a configuration file and checks a series of pid files to make
    sure that corresponding procsses are running. If they are not, it restarts them.
    
    The configuration file is in standard Python configparser format, which supports
    standard commenting and blank lines, etc.
    
    Each server is represented by a section of the config file, which is surrounded by []
    Each server has one line entries for:
    pidfile: <absolute path to the pid file for this server>
    cmdline: <start of the command string to be found in /proc/<processnum>/cmdline>
    startcommand: <shell command to start this server>
    restartcommand: <shell command to restart this server>
    stopcommand: <shell command to stop this server>
    starttime: <seconds to wait after restart before restarting dependent servers>
    cascaderestart: <dependent servers which must be restarted if this server is restarted>
    maxcpu: <percent of cpu utilization above which warning should be logged>
    maxmem: <megabytes of memory above which warning should be logged>
    
    Example for the Display Server"
    -----------------------
    [DisplayServer]
    pidfile: /tmp/display_server.pid
    cmdline: /usr/local/lib/ew/bin/display_server
    startcommand: /etc/init.d/display_server.sh start
    restartcommand: /etc/init.d/display_server.sh restart
    stopcommand: /etc/init.d/display_server.sh stop
    starttime: 3
    cascaderestart: Launcher
    ------------------------
    """
    def __init__(self,serverlistpath):
        """initializes the checker by reading the command file specified
        by <serverlistpath>"""
        self.servers = []
        if not os.path.exists(serverlistpath):
            raise Exception("Server list config file not found")
        self.checking = True
        try:
            self._readconfigfile(serverlistpath)
        except Exception, e:
            raise Exception("Problem reading server list %s" % e )
            
    # -------------------------------------------------------
    # Internal utility functions
    # -------------------------------------------------------
    def _readconfigfile(self,serverlistpath):
        """reads the config file and sets up the servers data structure"""
        self.servers = {}                       # named dictionary of servers
        self.exceptions = []                    # list of server names which should not be restarted
        c = ConfigParser.ConfigParser()
        if c.read(serverlistpath):
            for s in c.sections():
                itemdict = {}
                itemdict["name"] = s
                for item in c.items(s):
                    itemdict[item[0]] = item[1]
                #print "adding:",s,itemdict
                self.servers[s] = PidEntry(itemdict)
                #print self.servers
        else:
            logger.critical("Config file %s was unreadable" % configfn)
            raise Exception("Config file %s was unreadable" % configfn)
        #print self.servers
        for k in self.servers.keys():
            set = self._restartlist(k) 
            l = []
            for item in set:
                l.append(item.dict["name"])
            self.servers[k].dict["restartlist"] = l
            #print k, ":", self.servers[k].dict["restartlist"]
        self._createstartset()
    
    def _refreshexceptions(self):
        if os.path.exists(EXCEPTLOC):
            # logger.info("Exception file %s exists" % EXCEPTLOC)
            self.exceptions = filecontents(EXCEPTLOC).split()
            # logger.info("Exceptions %s" % repr(self.exceptions))
        else:
            self.exceptions = []
    
    def _isexception(self,servername):
        return servername in self.exceptions

    
    def _createrestartset(self,servername,restartset,restartstack):
        """_createrestartset(self,servername,restartset,restartstack) generates a list of servers that
        must be restarted by adding the contents of cascaderestart entries recursively. Since
        these entries might form an infinite loop, the function generates a restartstack to
        detect such loops and short circuit them. Such a loop indicates a design flaw where a set
        of servers has no atart order that guarantees correct behavior. The contents of this set
        are logged when such a loop is detected, but this routing picks an arbitrary start order for
        the set and hopes for the best rather than crashing. Logged messages indicating a loop MUST
        be corrected at the earlier possibility in the server code and the configuration file.
        """
        if servername not in restartstack:
            restartstack.append(servername)
            #print self.servers
            entry = self.servers[servername]
            restartset.add(entry)
            if "cascaderestart" in entry.dict:
                cascadedservers = entry.dict["cascaderestart"].split()
                for s in cascadedservers:
                    self._createrestartset(s,restartset,restartstack)
            restartstack.pop()
        else:
            logger.warning("%s appears to be in an infitine loop in %s" % (servername,restartstack))
                
    def _createstartset(self):
        """_createstartset(self) generates a list of servers for start of the system"""
        def _setserverpriority(servername, servers):
            entry = servers[servername]
            if "priority" in entry.dict:
                entry.dict["priority"] = int(entry.dict["priority"]) + 1
            else:
                entry.dict["priority"] = 1
            if "cascaderestart" in entry.dict:
                cascadedservers = entry.dict["cascaderestart"].split()
                for s in cascadedservers:
                    _setserverpriority(s,servers)
                    #print "%s priority is now %s" % (s,servers[s].dict["priority"])
                    
        restartset = set([])
        for s in self.servers.keys():
            entry = self.servers[s]
            restartset.add(entry)
            _setserverpriority(s,self.servers)
        return restartset


    def _restartlist(self,servername):
        """_orderedrestartlist(self,servername) creates a restart set for the specified server,
        which is a list of all servers which should be restarted when the specified server must
        be restarted. The set is then sorted into an ordered list.
        """
        restartset = set([])
        restartstack = []
        self._createrestartset(servername,restartset,restartstack)
        return restartset

    def _orderedrestartlist(self,servername):
        """_orderedrestartlist(self,servername) creates a restart set for the specified server,
        which is a list of all servers which should be restarted when the specified server must
        be restarted. The set is then sorted into an ordered list.
        """
        restartset = set([])
        restartstack = []
        self._createrestartset(servername,restartset,restartstack)
        #sl = sorted(restartset,cmp=compareentries)
        sl = sorted(restartset,key=lambda s:s.dict["priority"])
        return sl
           
    def _orderedstartlist(self):
        """_orderedstartlist(self) creates a restart set for the entire set of servers,
        which is a list of all servers which should be restarted when the specified server must
        be restarted. The set is then sorted into an ordered list.
        """
        restartset = self._createstartset()
        #sl = sorted(restartset,cmp=compareentries)
        sl = sorted(restartset, key=lambda s:s.dict["priority"])
        return sl
           
    def _restartitem(self,servername):
        """_restartitem(self,servername) restarts the specified server and then waits if a starttime
        parameter has been specified."""
        logger.info("%s is restarting (exceptions: %s)" % (servername,self.exceptions))
        if not self._isexception(servername):
            s = self.servers[servername]
            for k in s.dict.keys():
                if k.startswith("_"):
                    del s.dict[k]                                   # remove old statistics keys
            self._execute(s.dict["restartcommand"])
            if "starttime" in s.dict:
                time.sleep(int(s.dict["starttime"])) 


    def _execute(self,pgmpath):
        """execute(self,pgmpath) executes a command as a detached daemon
        """
        global PERFORMACTIONS
        cmd = pgmpath + " &"
        logger.info("executing '%s'" % cmd)
        if PERFORMACTIONS:
            os.system(cmd)
            
    def _compilestats(self,servername,pid):
        """_compilestats(self,servername,procid) reads the proc file system to compile cpu and
        memory usage statistics for a the specified server, and logs informational messages
        when the cpu or memory stats go outside limits specified in the config file.
        """
        havememdelta = False
        if servername in self.servers.keys():
            s = self.servers[servername]
            newstats = statprocess(pid)
            if newstats:
                t = time.time()
                if "_oldstats" in s.dict:
                    oldstats = s.dict["_oldstats"]
                    delta_u =  (float(newstats["utime"]) - float(s.dict["_oldstats"]["utime"])) / HZ
                    delta_s =  (float(newstats["stime"]) - float(s.dict["_oldstats"]["stime"])) / HZ
                    delta_t = t - s.dict["_oldtime"]
                    s.dict["_cpu"] = ((delta_u / delta_t) + (delta_s / delta_t)) * 100
                    s.dict["_rss"] = newstats["rss"]
                    if (newstats["rss"] == oldstats["rss"]):
                        havememdelta = False
                    else:
                        havememdelta = True
                    #print servername, ":", s.dict["_cpu"], s.dict["_rss"]
                s.dict["_oldstats"] = newstats
                s.dict["_oldtime"] = t
            
            if "_cpu" in s.dict and "maxcpu" in s.dict:
                if float(s.dict["_cpu"]) > float(s.dict["maxcpu"]):
                    logger.warning("%s is above its CPU limit: %s > %s" % (servername,s.dict["_cpu"],s.dict["maxcpu"]))
            
            if "_rss" in s.dict and "maxmem" in s.dict:
                if int(s.dict["_rss"]) > (int(s.dict["maxmem"]) * 1000000):
                    if havememdelta:
                        logger.warning("%s is above its memory use limit: %s > %s mbytes" % (servername,s.dict["_rss"],s.dict["maxmem"]))
            

            
    
    # -------------------------------------------------------
    # API
    # -------------------------------------------------------
    def restartserver(self,servername):
        if not self._isexception(servername):
            list = self._orderedrestartlist(servername)
            for item in list:
                self._restartitem(item.dict["name"])
        
    def stopserver(self,servername, proclist=None):
        s = self.servers[servername] 
        p = checkpid(s.dict["pidfile"],s.dict["cmdline"])
        if p:
            # program is running, shut it down
            if PERFORMKILL:
                if proclist:
                    proclist.append(p)
                logger.info("sending stop command '%s' to %s (%s)" % (s.dict["stopcommand"],p,s.dict["name"]))
                self._execute(s.dict["stopcommand"])
            else:
                logger.info("simulating stop command '%s' to %s (%s)" % (s.dict["stopcommand"],p,s.dict["name"]))
    
    
    def setchecking(self,bool):

        """setchecking(self,bool) sets the checking flag, allowing graceful shutdown
        without a race condition between the restart monitor and the servers that are
        shutting down.  """

        self.checking = bool

    def checkandrestart(self):

        """checkandrestart(self) is the main checking loop of the restart servers. It
        periodically checks each server and restarts it if need be, compiling usage
        statistics as it checks the servers.  """

        global CHECK_WAIT
        while self.checking: 
            for k in self.servers.keys():
                s = self.servers[k]
                p = procid(s.dict["pidfile"], shouldlog = False)
                if p:
                    self._compilestats(k,p)
                if self._isexception(k):
                    # stop the program
                    self.stopserver(k)
                elif not checkpid(s.dict["pidfile"],s.dict["cmdline"]):
                    # restart the program
                    self.restartserver(k)
            time.sleep(CHECK_WAIT)
            self._refreshexceptions()
    
    def start(self):

        """start(self) takes to properly ordered start list and starts the servers one
        by one."""

        logger.info("---\n---\n---\nSystem Start\n---\n---\n---")
        list = self._orderedstartlist()
        logger.info("start list %s" % list)
        for item in list:
            self._restartitem(item.dict["name"])
    
    def hardkillserver(self,servername):
        """hardkillserver(self,servername) finds the process and does a kill -9 on it
        """
        s = self.servers[servername]
        p = checkpid(s.dict["pidfile"],s.dict["cmdline"])
        if p:
            # program is running, shut it down
                logger.info("%s performing hard kill of %s (%s)" % (APP,p,s.dict["name"]))
                os.system("kill -9 %s" % p)
    
    def shutdownall(self):
        """shutdownall(self) gracefully shuts down all servers, by first calling their shutdown
        script and then after a specified interval using kill -9 to shutdown the servers.
        """
        global SHUTDOWN_WAIT, logger
        self.setchecking(False)
        proclist = []
        logger.info("*** Initiating graceful shutdown of servers *** ----------------------------")
        
        # send all of the processes an initial shutdown
        for k in self.servers.keys():
            self.stopserver(k, proclist)
            
        # wait a bit for programs to settle down and quit
        time.sleep(SHUTDOWN_WAIT)
        
        # now loop trying to kill all processes which have not shut down
        alldone = False
        while not alldone:
            alldone = True
            for pid in proclist:
                if testproc(pid):
                    alldone = False
                    # program is running, shut it down
                    if PERFORMKILL:
                        logger.warning("sending SIGKILL to %s" % (pid))
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except:
                            logger.error("could not kill %s" % (pid))
                    else:
                        logger.warning("simulating sending SIGKILL to %s" % (pid))
            logger.warning("Shutdown attempt continues: %s" % (alldone))
            time.sleep(SHUTDOWN_RETRY_WAIT)
                    
            
