"""
  Mark Liebrand 2024
  This file is part of FindMyGUI which is released under the Apache 2.0 License
  See file LICENSE or go to for full license details https://github.com/liebrandapps/FindMyGUI
"""
import base64
import glob
import json
import logging
import signal
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from os import makedirs, chmod
from os.path import join, exists, splitext
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

from Crypto.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_OAEP, AES
from Cryptodome.Hash import SHA256, HMAC
from Cryptodome.Random import get_random_bytes

from airTag import AirTag
from api import API
from config import Config
from context import Context
from daemon import Daemon
from mqtt import MQTT

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
            f"[loadAirTags] Airtags Directory '{airTagDir}' does not exist, creating it. This will be used to store "
            f"Airtag key information.")
        makedirs(airTagDir)
    tags = glob.glob(join(airTagDir, '*' + airTagSuffix))
    for t in tags:
        airtag = AirTag(ctx, jsonFile=t)
        ctx.airtags[airtag.id] = airtag


def getKeys():
    global ctx
    if ctx.privKey is None:
        ctx.log.info(f"[getKeys] Generating key for encrypted MQTT communication")
        key = RSA.generate(2048)
        ctx.privKey = base64.b64encode(key.exportKey('DER')).decode('ascii')
        ctx.save()


def mqttCBKey(topic, payload):
    global ctx
    ctx.log.debug(f"[MQTT] Received {payload}")
    jsn = json.loads(payload)
    key = RSA.importKey(base64.b64decode(ctx.privKey))
    publicKey = key.publickey()
    resp = {'uid': jsn['uid'], 'publicKey': base64.b64encode(publicKey.exportKey('DER')).decode('ascii')}
    ctx.mqtt.publish(jsn['responseTopic'], resp)


def mqttCBAirTag(topic, payload):
    global ctx
    ctx.log.debug(f"[MQTT] Received {payload}")
    jsn = json.loads(payload)
    key = RSA.importKey(base64.b64decode(ctx.privKey))
    encData = base64.b64decode(jsn['encData'])
    cipher_rsa = PKCS1_OAEP.new(key)
    aesKey = cipher_rsa.decrypt(encData)
    ctx._aesKeys[jsn['uid']] = aesKey
    resp = {'uid': jsn['uid']}
    for airtag in ctx.airtags.values():
        cipher = AES.new(aesKey, AES.MODE_CTR)
        dta = airtag.toJSON()
        ciphertext = cipher.encrypt(dta.encode('utf-8'))
        resp['encDta'] = base64.b64encode(ciphertext).decode('ascii')
        resp['nonce'] = base64.b64encode(cipher.nonce).decode('ascii')
        ctx.mqtt.publish(jsn['responseTopic'], resp)


def mqttCBLocationUpdate(topic, payload):
    global ctx
    ctx.log.debug(f"[MQTT] Location update received {payload}")
    jsn = json.loads(payload)
    if jsn['uid'] not in ctx.aesKeys:
        # request aeskey ...
        mqttCBKey(topic, payload)
    else:
        nonce = base64.b64decode(jsn['nonce'])
        aesKey = ctx.aesKeys[jsn['uid']]
        cipher = AES.new(aesKey, AES.MODE_CTR, nonce=nonce)
        encData = base64.b64decode(jsn['encDta'])
        clearData = cipher.decrypt(encData).decode('utf-8')
        jsn = json.loads(clearData)
        if not jsn['known']:
            advKey = jsn['advKey']
            for airtag in ctx.airtags.values():
                if airtag.advertisementKey == advKey:
                    cipher = AES.new(aesKey, AES.MODE_CTR)
                    dta = airtag.toJSON()
                    ciphertext = cipher.encrypt(dta.encode('utf-8'))
                    resp = {'uid': jsn['uid'], 'encDta': base64.b64encode(ciphertext).decode('ascii'),
                            'nonce': base64.b64encode(cipher.nonce).decode('ascii')}
                    ctx.mqtt.publish(jsn['responseTopic'], resp)
                    airtag.updateLocation(jsn['timestamp'], jsn['lat'], jsn['lon'], direct=True)
                    break
        if jsn['known'] and jsn['tagId'] in ctx.airtags.keys():
            airtag = ctx.airtags[jsn['tagId']]
            airtag.updateLocation(jsn['timestamp'], jsn['lat'], jsn['lon'], jsn['status'], direct=True)


class FindMyServer(BaseHTTPRequestHandler):
    """ Extension: ContentType, Encode """
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
        },
        "mqtt": {
            "enable": ["Boolean", False],
            "server": ["String", ],
            "port": ["Integer", 1883],
            "user": ["String", ""],
            "password": ["String", ],
            "keepAlive": ["Integer", 60],
            "subscribeTopic": ["String", None],
            "retainedMsgs": ["Boolean", False],
            "debug": ["Boolean", False],
            "reconnect": ["Integer", 24, "Reconnect every 24 hours"],
            "silent": ["Boolean", False, "If set to true, no received mqtt messages are logged. (Default: False)"],
            "topic": ["String", "findmygui/app/"],
        },
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
    ctx.load()
    if cfg.mqtt_enable:
        getKeys()
        mqtt = MQTT(ctx)
        mqtt.start()
        ctx.mqtt = mqtt
        mqtt.subscribe(cfg.mqtt_topic + "key_request", mqttCBKey)
        mqtt.subscribe(cfg.mqtt_topic + "airtag_request", mqttCBAirTag)
        mqtt.subscribe(cfg.mqtt_topic + "location_update", mqttCBLocationUpdate)

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
