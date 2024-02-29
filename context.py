"""
  Mark Liebrand 2024
  This file is part of FindMyGUI which is released under the Apache 2.0 License
  See file LICENSE or go to for full license details https://github.com/liebrandapps/FindMyGUI
"""
import json
import threading
from datetime import datetime
from os.path import exists


class Context:
    statusFile = "./findMyGUI.json"

    def __init__(self, cfg, log):
        self.__log = log
        self.__cfg = cfg
        self.__threadMonitor = {}
        self.startTime = datetime.now()
        self.__airtags = {}
        self._signInDone = False
        self._requestCreds = 0
        self._requestAuth = 0
        self._userName = ""
        self._password = ""
        self._ndFactor = ""
        self._errMsg = ""
        self._lastLocationUpdate = 0
        self._usedReports = 0

    def load(self):
        if exists(Context.statusFile):
            with open(Context.statusFile) as f:
                dta = json.load(f)
            self._lastLocationUpdate = dta['lastLocationUpdate']
            if 'usedReports' in dta:
                self._usedReports = dta['usedReports']

    def save(self):
        j = {"lastLocationUpdate": self._lastLocationUpdate, "usedReports": self._usedReports}
        with open(Context.statusFile, 'w') as f:
            print(json.dumps(j, indent=4), file=f)

    @property
    def log(self):
        return self.__log

    @property
    def cfg(self):
        return self.__cfg

    @property
    def airtags(self):
        return self.__airtags

    @property
    def threadMonitor(self):
        return self.__threadMonitor

    def checkThreads(self, now):
        missing = []
        for k in self.__threadMonitor.keys():
            if (now - self.__threadMonitor[k][0]).seconds > 900:
                # thread has not updated since 15 minutes
                self.__log.warn("[CTX] Thread for class %s has not sent an alive message for %d seconds" %
                                (k, (now - self.__threadMonitor[k][0]).seconds))
                missing.append(self.__threadMonitor[k])
        return missing

    def uptime(self, now):
        days = (now - self.startTime).days
        secs = (now - self.startTime).seconds
        hours = int((secs % 86400) / 3600)
        minutes = int((secs % 3600) / 60)
        seconds = int(secs % 60)

        up = ""
        if days > 0:
            up += str(days) + " " + (days == 1 and "day" or "days") + ", "
        if len(up) > 0 or hours > 0:
            up += str(hours) + " " + (hours == 1 and "hour" or "hours") + ", "
        if len(up) > 0 or minutes > 0:
            up += str(minutes) + " " + (minutes == 1 and "minute" or "minutes") + ", "
        up += str(seconds) + " " + (seconds == 1 and "second" or "seconds")
        return up

    @property
    def requestCreds(self):
        return self._requestCreds

    @requestCreds.setter
    def requestCreds(self, value):
        self._requestCreds = value

    @property
    def requestAuth(self):
        return self._requestAuth

    @requestAuth.setter
    def requestAuth(self, value):
        self._requestAuth = value

    @property
    def signInDone(self):
        return self._signInDone

    @signInDone.setter
    def signInDone(self, value):
        self._signInDone = value

    @property
    def userName(self):
        return self._userName

    @userName.setter
    def userName(self, value):
        self._userName = value

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value

    @property
    def ndFactor(self):
        return self._ndFactor

    @ndFactor.setter
    def ndFactor(self, value):
        self._ndFactor = value

    @property
    def errMsg(self):
        return self._errMsg

    @errMsg.setter
    def errMsg(self, value):
        self._errMsg = value

    @property
    def lastLocationUpdate(self):
        return self._lastLocationUpdate

    @lastLocationUpdate.setter
    def lastLocationUpdate(self, value):
        self._lastLocationUpdate = value
        self.save()

    @property
    def usedReports(self):
        return self._usedReports

    @usedReports.setter
    def usedReports(self, value):
        self._usedReports = value
        self.save()
