import glob
import logging
import signal
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from os import makedirs
from os.path import join, exists, splitext
from threading import Thread
from urllib.parse import parse_qs, urlparse

from airTag import AirTag
from api import API
from config import Config
from context import Context
from daemon import Daemon

APP = "findMyGUI"
CONFIG_DIR = "./"
CONFIG_FILE = "findMyGUI.ini"


def setupLogger():
    global runAsDaemon
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


def terminate(sigNo, _):
    global doTerminate
    global myServer
    global httpIsRunning
    if doTerminate:
        return
    doTerminate = True
    ctx.log.info(f"[{APP}] Terminating with Signal {sigNo} {sigs[sigNo]}")
    if httpIsRunning:
        Thread(target=myServer.shutdown).start()


def loadAirTags():
    global ctx
    airTagDir = ctx.cfg.general_airTagDirectory
    airTagSuffix = ctx.cfg.general_airTagSuffix
    if not exists(airTagDir):
        ctx.log.info(
            f"[loadAirTags] Airtags Directory '{airTagDir}' does not exist, creating it. This will be used to store Airtag key information.")
        makedirs(airTagDir)
    tags = glob.glob(join(airTagDir, '*' + airTagSuffix))
    for t in tags:
        airtag = AirTag(ctx, jsonFile=t)
        ctx.airtags[airtag.id] = airtag


class FindMyServer(BaseHTTPRequestHandler):
    ''' Extension: ContentType, Encode '''
    contentTypeDct = {'.html': ["text/html", True],
                      '.js': ["application/javascript", True],
                      '.css': ["text/css", True],
                      '.png': ["image/png", False],
                      }

    def do_GET(self):
        if self.path.startswith('/api'):
            api = API(ctx)
            query_components = parse_qs(urlparse(self.path).query)
            cmd = query_components["command"]
            result = api.call(cmd[0], params=query_components)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(result.encode('UTF-8'))
        else:
            file = "/index.html" if self.path == "/" else self.path
            file = join('www', file[1:])
            ext = splitext(file)[1]
            ct = self.contentTypeDct[ext] if ext in self.contentTypeDct.keys() else None
            if exists(file) and ct is not None:
                contentType = ct[0]
                encode = ct[1]
                self.send_response(200)
                self.send_header("Content-type", contentType)
                self.end_headers()
                with open(file, 'r' if encode else 'rb') as f:
                    data = f.read()
                self.wfile.write(data.encode('UTF-8') if encode else data)
            else:
                self.send_response(404)
                self.end_headers()


if __name__ == '__main__':
    doTerminate = False
    initialConfig = {
        "general": {
            "httpHost": ['String', '0.0.0.0'],
            "httpPort": ['Integer', 8008],
            "httpFiles": ['String', 'www'],
            "anisetteHost": ['String', 'http://192.168.2.15'],
            "anisettePort": ['Integer', 6969],
            "airTagDirectory": ['String', 'airtags'],
            "airTagSuffix": ['String', '.json'],
            "history": ["Integer", 30],
        },
        "logging": {
            "logFile": ["String", "/tmp/findMyGUI.log"],
            "maxFilesize": ["Integer", 1000000],
            "msgFormat": ["String", "%(asctime)s, %(levelname)s, %(module)s {%(process)d}, %(lineno)d, %(message)s"],
            "logLevel": ["Integer", 10],
            "stdout": ["Boolean", True],
        },
        "appleId": {
            "appleId": ["String", ''],
            "password": ["String", ''],
            "trustedDevice": ["Boolean", False],
        }
    }
    path = join(CONFIG_DIR, CONFIG_FILE)
    if not (exists(path)):
        print(f"[{APP}] No config file {CONFIG_FILE} found at {CONFIG_DIR}, using defaults")
    cfg = Config(path)
    cfg.addScope(initialConfig)
    runAsDaemon = False
    if len(sys.argv) > 1:
        todo = sys.argv[1]
        if todo in ['start', 'stop', 'restart', 'status']:
            runAsDaemon = True
            pidFile = cfg.general_pidFile
            logFile = cfg.logging_logFile
            d = Daemon(pidFile, APP, logFile)
            d.startstop(todo, stdout=logFile, stderr=logFile)
    log = setupLogger()
    if log is None:
        sys.exit(-126)
    ctx = Context(cfg, log)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    sigs = {signal.SIGINT: signal.SIGINT.name,
            signal.SIGTERM: signal.SIGTERM.name}

    httpHost = cfg.general_httpHost
    httpPort = cfg.general_httpPort

    loadAirTags()

    myServer = ThreadingHTTPServer((httpHost, httpPort), FindMyServer)
    log.info(f"[{APP}] HTTP Server is starting: {httpHost}:{httpPort}")
    httpIsRunning = True
    try:
        myServer.serve_forever()
    finally:
        httpIsRunning = False
        myServer.server_close()
    log.info(f"{APP} HTTP Server is terminating: {httpHost}:{httpPort}")
