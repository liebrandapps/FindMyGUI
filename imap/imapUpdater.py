import datetime
import glob
import imaplib
import logging
import sys
import threading
import urllib.parse
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler
from os import makedirs
from os.path import join, exists
from time import time

from airTag import AirTag
from api import API
from config import Config
from context import Context
from main import APP


class IMAPUpdater(threading.Thread):
    TAG = "[IMAP]"
    THREAD_ID = "IMAP Updater"

    def __init__(self, context):
        threading.Thread.__init__(self, name=IMAPUpdater.THREAD_ID)
        self.ctx = context
        self.mail = None
        self._terminate = False
        self.event = threading.Event()
        self._interval = ctx.cfg.imap_interval

    def run(self):
        self._terminate = False
        log = self.ctx.log
        log.info(f"{IMAPUpdater.TAG} Starting Thread {IMAPUpdater.THREAD_ID}")
        api = API(ctx)
        while not self._terminate:
            self.event.wait(self._interval * 60)
            self.event.clear()
        log.info(f"{IMAPUpdater.TAG} Stopping Thread {IMAPUpdater.THREAD_ID}")

    def terminate(self):
        self._terminate = True
        self.event.set()

    def login(self):
        cfg = self.ctx.cfg
        if cfg.imap_useSSL:
            self.mail = imaplib.IMAP4_SSL(host=cfg.imap_host)
        else:
            self.mail = imaplib.IMAP4(host=cfg.imap_host)
        self.mail.login(cfg.imap_user, cfg.imap_password)
        found = False
        status, lst = self.mail.list()
        for f in lst:
            tmp = f.decode('UTF-8')
            tmp1 = tmp.split('"."')
            folder = tmp1[1].strip()
            if folder == cfg.imap_folder:
                found = True
                break
        if not found:
            self.mail.create(cfg.imap_folder)

    def logout(self):
        self.mail.logout()

    def storeMessagePlain(self):
        msg = Message()
        msg['From'] = self.ctx.cfg.imap_sender
        msg['Subject'] = "AirTag Location Update"
        msg.set_payload("Test")
        self.mail.append(self.ctx.cfg.imap_folder, '', imaplib.Time2Internaldate(time()), str(msg).encode('utf-8'))

    def storeMessageHtml(self):
        gMapUrl = "https://www.google.com/maps/dir/"
        bingUrl = "https://bing.com/maps/default.aspx?sp="
        ctrlong = 0
        ctrlat = 0
        cnt = 0
        pts = ""
        imgUrl = "https://github.com/liebrandapps/FindMyGUI/blob/master/www/"
        for tag in ctx.airtags.values():
            name = tag.name
            longitude = tag.longitude
            latitude = tag.latitude
            lastSeen = datetime.datetime.fromtimestamp(tag.lastSeen)
            imgId = tag.imgId
            gMapUrl += "/" + str(latitude) + "," + str(longitude)
            if len(pts) > 0:
                pts += "~"
            pts += "point." + str(latitude) + "_" + str(longitude) + "_" + urllib.parse.quote_plus(name) + \
                   "_" + urllib.parse.quote_plus("Last Update: " + lastSeen.strftime("%H:%M:%S %d.%m.%Y")) + \
                   "_" + urllib.parse.quote_plus("https://github.com/liebrandapps") + \
                   "_" + urllib.parse.quote_plus(imgUrl + imgId + ".png?raw=true")
            ctrlong += longitude
            ctrlat += latitude
            cnt += 1
        bingUrl += pts
        msg = MIMEMultipart('alternative')
        msg['From'] = self.ctx.cfg.imap_sender
        msg['Subject'] = "AirTag Location Update"
        text = "AirTag Location Update\n\n" + bingUrl
        html = """\
        <html>
          <head>
          </head>
          <body>
            <p>Hi!<br>
               List of locations<br>
               Click this link to open in browser <a href=" """
        html += bingUrl
        html += """">link</a>.
            </p>
                
          </body>
        </html>
        """
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        msg.attach(part1)
        msg.attach(part2)
        self.mail.append(self.ctx.cfg.imap_folder, '', imaplib.Time2Internaldate(time()), str(msg).encode('utf-8'))


CONFIG_DIR = "./"
CONFIG_FILE = "findMyGUI.ini"


def setupLogger():
    global runAsDaemon
    global cfg
    try:
        _log = logging.Logger(APP)
        loghdl = RotatingFileHandler(cfg.logging_logFile, 'a', cfg.logging_maxFilesize, 4)
        loghdl.setFormatter(logging.Formatter(cfg.logging_msgFormat))
        loghdl.setLevel(cfg.logging_logLevel)
        _log.addHandler(loghdl)
        if cfg.logging_stdout and not runAsDaemon:
            loghdl = logging.StreamHandler(sys.stdout)
            loghdl.setFormatter(logging.Formatter(cfg.logging_msgFormat))
            loghdl.setLevel(cfg.logging_logLevel)
            _log.addHandler(loghdl)
        _log.disabled = False
        return _log
    except Exception as e:
        print("[%s] Unable to initialize logging. Reason: %s" % (APP, e))
        return None


def loadAirTags():
    global ctx
    airTagDir = ctx.cfg.general_airTagDirectory
    airTagSuffix = ctx.cfg.general_airTagSuffix
    if not exists(airTagDir):
        ctx.log.info(
            f"[loadAirTags] Airtags Directory '{airTagDir}' does not exist, creating it. This will be used to store "
            f"Airtag key information.")
        makedirs(airTagDir)
    tags = glob.glob(join(airTagDir, '*' + airTagSuffix))
    for t in tags:
        airtag = AirTag(ctx, jsonFile=t)
        ctx.airtags[airtag.id] = airtag


if __name__ == '__main__':
    initialConfig = {
        "general": {
            "httpHost": ['String', '0.0.0.0'],
            "httpPort": ['Integer', 8008],
            "httpFiles": ['String', 'www'],
            "anisetteHost": ['String', None],
            "anisettePort": ['Integer', 6969],
            "airTagDirectory": ['String', '../airtags'],
            "airTagSuffix": ['String', '.json'],
            "history": ["Integer", 30],
            "automaticQuery": ["Integer", 0],
        },
        "logging": {
            "logFile": ["String", "/tmp/findMyGUI.log"],
            "maxFilesize": ["Integer", 1000000],
            "msgFormat": ["String", "%(asctime)s, %(levelname)s, %(module)s {%(process)d}, %(lineno)d, %(message)s"],
            "logLevel": ["Integer", 10],
            "stdout": ["Boolean", True],
        },

        "imap": {
            "host": ['String', None],
            "user": ['String', None],
            "password": ['String', None],
            "useSSL": ['Boolean', True],
            "folder": ['String', 'airtag'],
            "sender": ['FindMyGUI'],
        },
    }
    path = join(CONFIG_DIR, CONFIG_FILE)
    if not (exists(path)):
        print(f"[] No config file {CONFIG_FILE} found at {CONFIG_DIR}, using defaults")
    cfg = Config(path)
    cfg.addScope(initialConfig)
    runAsDaemon = False
    log = setupLogger()
    ctx = Context(cfg, log)

    loadAirTags()

    imap = IMAPUpdater(ctx)

    imap.login()
    imap.storeMessageHtml()
    imap.logout()
