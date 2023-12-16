"""
  Mark Liebrand 2024
  This file is part of FindMyGUI which is released under the Apache 2.0 License
  See file LICENSE or go to for full license details https://github.com/liebrandapps/FindMyGUI
"""
import os
import signal
import sys
import time
import psutil


class Daemon:

    def __init__(self, pidFile, app, logFile):
        self.pidFile = pidFile
        self.logFile = logFile
        self.app = app

    @staticmethod
    def getTimeStamp():
        return time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(time.time()))

    @staticmethod
    def printLogLine(file, message):
        file.write('%s %s\n' % (Daemon.getTimeStamp(), message))
        file.flush()

    def startstop(self, todo, stdout="/dev/null", stderr=None, stdin="/dev/null"):
        try:
            pf = open(self.pidFile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if 'stop' == todo or 'restart' == todo:
            if not pid:
                msg = "[%s] Could not stop. Pidfile %s is missing\n" % (self.app, self.pidFile)
                Daemon.printLogLine(sys.stderr, msg)
                sys.exit(1)
            Daemon.printLogLine(sys.stdout, "[%s] Stopping Process with PID %d" % (self.app, pid))
            try:
                cnt = 10
                while 1:
                    if cnt < 0:
                        os.kill(pid, signal.SIGKILL)
                    else:
                        os.kill(pid, signal.SIGTERM)
                    time.sleep(3)
                    cnt -= 1
            except OSError as err:
                err = str(err)
                if err.find("No such process") > 0:
                    if "stop" == todo:
                        if os.path.exists(self.pidFile):
                            os.remove(self.pidFile)
                        sys.exit(0)
                    todo = "start"
                    pid = None
                else:
                    print(str(err))
                    sys.exit(1)
        if 'start' == todo:
            if pid:
                msg = "[%s] Start aborted since Pidfile %s exists" % self.app
                Daemon.printLogLine(sys.stderr, msg % self.pidFile)
                sys.exit(1)
            Daemon.printLogLine(sys.stdout, "[%s] Starting Process as Daemon" % self.app)
            self.daemonize(stdout, stderr, stdin)
        if 'status' == todo:
            if pid:
                logFileStatus = os.path.exists(self.logFile)
                if logFileStatus:
                    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(self.logFile)
                    logLastModified = time.ctime(mtime)
                else:
                    logLastModified = "never"
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    with process.oneshot():
                        msg = "[%s] Process with pid %d is running [%s], last log update [%s]" \
                              % (self.app, pid, process.name(), logLastModified)
                        self.printLogLine(sys.stdout, msg)
                        sys.exit(0)
                else:
                    msg = "[%s] Process with pid %d is NOT running, but we have a PID file - maybe it crashed. Last " \
                          "log update [%s]" % (self.app, pid, logLastModified)
                    self.printLogLine(sys.stdout, msg)
                    if os.path.exists(self.pidFile):
                        os.remove(self.pidFile)
                        sys.exit(3)
            else:
                msg = "[%s] Process seems to be not running - no PIDFile (%s) found." % (self.app, self.pidFile)
                self.printLogLine(sys.stderr, msg)
                sys.exit(0)

    def daemonize(self, stdout='/dev/null', stderr=None, stdin='/dev/null'):
        if not stderr:
            stderr = stdout
        si = open(stdin, 'r')
        so = open(stdout, 'a+')
        se = open(stderr, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("[%s] fork #1 failed (%d) %s" % (self.app, e.errno, e.strerror))
            sys.exit(1)

        os.umask(0)
        os.setsid()

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("[%s] fork #2 failed (%d) %s" % (self.app, e.errno, e.strerror))
            sys.exit(1)
        pid = str(os.getpid())
        self.printLogLine(sys.stdout, "[%s] Process started as Daemon with pid %s" % (self.app, pid))
        if self.pidFile:
            open(self.pidFile, 'w+').write('%s\n' % pid)
