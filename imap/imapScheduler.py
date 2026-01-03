import json
import threading
from datetime import datetime

from api import API
from imap.imapUpdater import IMAPUpdater


class IMAPScheduler(threading.Thread):
    CLS = "Scheduler"

    def __init__(self, ctx):
        threading.Thread.__init__(self, name=IMAPScheduler.CLS)
        self.ctx = ctx
        self.log = ctx.log
        self.cfg = ctx.cfg
        self.__terminate = False
        self.__wakeup = threading.Event()
        self.interval = self.cfg.general_automaticQuery * 60

    def run(self):
        self.log.info(f"[{IMAPScheduler.CLS}] Starting Scheduler")
        self.ctx.threadMonitor[self.__class__.__name__] = [datetime.now(), IMAPScheduler.CLS]
        while not self.__terminate:
            now = datetime.now()
            if self.ctx.automaticUpdatePossible and not self.ctx.queryInProgress and \
                    (now - datetime.fromtimestamp(self.ctx.lastLocationUpdate)).total_seconds() > (self.ctx.cfg.general_automaticQuery*60):
                api = API(self.ctx)
                result = json.loads(api.call('refresh'))
                if result['status'] == 'ok':
                    imap = IMAPUpdater(self.ctx)
                    imap.login()
                    if self.ctx.cfg.imap_removeOldReports:
                        imap.removeOldReports()
                    imap.storeMessageHtml()
                    imap.notifyEventCount()
                    imap.logout()
            self.__wakeup.wait(self.interval)
            self.__wakeup.clear()
            self.ctx.threadMonitor[self.__class__.__name__] = [datetime.now(), IMAPScheduler.CLS]
        self.log.info(f"[{IMAPScheduler.CLS}] Finishing Scheduler")
        del self.ctx.threadMonitor[self.__class__.__name__]

    def terminate(self):
        self.__terminate = True
        self.__wakeup.set()
