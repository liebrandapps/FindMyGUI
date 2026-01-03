import base64
import hashlib
import json
import math
import string
import uuid
from datetime import datetime, timedelta
from os.path import join
from random import SystemRandom


def calculateDistance(lonlatA, lonlatB):
    dx = 71.5 * (lonlatA[0] - lonlatB[0])
    dy = 111.3 * (lonlatA[1] - lonlatB[1])
    distance = math.sqrt(dx * dx + dy * dy)
    return distance * 1000


class AirTag:

    def __init__(self, ctx, jsonFile=None):
        self.log = ctx.log
        self.cfg = ctx.cfg
        self.__id = uuid.uuid4().hex
        self._name = ""
        self._privateKey = None
        self._advertisementKey = None
        self._hashedKey = None
        self._needsSave = False
        self._lastSeen = None
        self._latitude = None
        self._longitude = None
        self._direct = False
        self._history = {}
        self._imgId = "airtag"
        self._status = 0
        self._hasBattery = False
        self._batteryLevel = 0
        self._eventCount = 0
        self._updated = False
        self._enableGeoFencing = 'disable'
        self._trustedTagId = None
        self._trustedLocationName = None
        self._trustedLocationLat = None
        self._trustedLocationLon = None
        self._distance = 0
        self._eventCountChanged = False
        self._notifyEvent = False
        self._notifyText = ""
        self._appleId = None
        if jsonFile is None:
            airTagDir = ctx.cfg.general_airTagDirectory
            airTagSuffix = ctx.cfg.general_airTagSuffix
            self.fileName = join(airTagDir, self.__id + airTagSuffix)
            self._needsSave = True
        else:
            self.fileName = jsonFile
            self.load(jsonFile)

    @property
    def id(self):
        return self.__id

    def load(self, jsonFile):
        with open(jsonFile) as f:
            dta = json.load(f)
        self._name = dta['name']
        self._privateKey = base64.b64decode(dta['privateKey'])
        self._advertisementKey = base64.b64decode(dta['advertisementKey'])
        s256 = hashlib.sha256()
        s256.update(self._advertisementKey)
        self._hashedKey = base64.b64encode(s256.digest()).decode("ascii")
        if 'id' in dta.keys():
            self.__id = dta['id']
        else:
            self.save()
        if 'lastSeen' in dta.keys():
            self._lastSeen = dta['lastSeen']
            self._longitude = dta['longitude']
            self._latitude = dta['latitude']
        if 'history' in dta.keys():
            self._history = dta['history']
        if 'imgId' in dta.keys():
            self._imgId = dta['imgId']
        if 'direct' in dta.keys():
            self._direct = dta['direct']
        if 'status' in dta.keys():
            self._status = dta['status']
            self._updateBatteryLevel(self._status)
        if 'hasBattery' in dta.keys():
            self._hasBattery = dta['hasBattery']
            self._eventCount = dta['eventCount']
        if 'updated' in dta.keys():
            self._updated = dta['updated']
        if 'enableGeoFencing' in dta.keys():
            self._enableGeoFencing = dta['enableGeoFencing']
            self._trustedTagId = dta['trustedTagId']
            self._trustedLocationName = dta['trustedLocationName']
            self._trustedLocationLat = float(dta['trustedLocationLat']) if dta[
                                                                               'trustedLocationLat'] is not None else 0.0
            self._trustedLocationLon = float(dta['trustedLocationLon']) if dta[
                                                                               'trustedLocationLon'] is not None else 0.0
            self._distance = int(dta['distance']) if dta['distance'] is not None else 0
        if 'appleId' in dta.keys():
            self._appleId = dta['appleId']
        self._eventCountChanged = dta['eventCountChanged'] if 'eventCountChanged' in dta.keys() else False
        self._notifyEvent = dta['notifyEvent'] if 'notifyEvent' in dta.keys() else False
        self._notifyText = dta['notifyText'] if 'notifyText' in dta.keys() else ''
        self.log.info(f"Loaded AirTag [{self._name} / {self.__id}] from file {self.fileName}")
        self._needsSave = False

    def save(self):
        toRemove = []
        cutOff = datetime.now() - timedelta(days=self.cfg.general_history)
        for h in self._history.keys():
            if int(float(h)) < cutOff.timestamp():
                toRemove.append(h)
        for r in toRemove:
            del self._history[r]
        j = self.toJSON()
        with open(self.fileName, 'w') as f:
            print(j, file=f)
        self.log.info(f"Saved AirTag [{self._name} / {self.__id}] to file {self.fileName}")
        self._needsSave = False

    @property
    def needsSave(self):
        return self._needsSave

    def toJSON(self):
        return json.dumps(self.toDict(), indent=4)

    def toDict(self):
        return {'name': self._name,
                'privateKey': base64.b64encode(self._privateKey).decode('ascii'),
                'advertisementKey': base64.b64encode(self._advertisementKey).decode('ascii'),
                'lastSeen': self._lastSeen,
                'longitude': self._longitude,
                'latitude': self._latitude,
                'direct': self._direct,
                'history': self._history,
                'imgId': self._imgId,
                'status': self._status,
                'hasBattery': self._hasBattery,
                'batteryLevel': self._batteryLevel,
                'eventCount': self._eventCount,
                'eventCountChanged': self._eventCountChanged,
                'notifyEvent': self._notifyEvent,
                'notifyText': self._notifyText,
                'updated': self._updated,
                'id': self.id,
                'enableGeoFencing': self._enableGeoFencing,
                'trustedTagId': self._trustedTagId,
                'trustedLocationName': self._trustedLocationName,
                'trustedLocationLat': self._trustedLocationLat,
                'trustedLocationLon': self._trustedLocationLon,
                'distance': self._distance,
                'appleId': self._appleId
                }

    def resolveTag(self, tag):
        value = "notFound"
        if tag == '##NAME##':
            value = self._name
        if tag == '##ID##':
            value = self.id
        if tag == '##LASTSEEN##':
            if self._lastSeen is None or int(self._lastSeen) == 0:
                value = "Never"
            else:
                value = datetime.utcfromtimestamp(self._lastSeen).strftime('%H:%M:%S %d.%m.%Y')
        return value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._needsSave = self._needsSave or (value != self._name)
        self._name = value

    @property
    def privateKey(self):
        return base64.b64encode(self._privateKey).decode('ascii')

    @privateKey.setter
    def privateKey(self, value):
        v = base64.b64decode(value)
        self._needsSave = self._needsSave or (v != self._privateKey)
        self._privateKey = v

    @property
    def advertisementKey(self):
        return base64.b64encode(self._advertisementKey).decode('ascii')

    @advertisementKey.setter
    def advertisementKey(self, value):
        v = base64.b64decode(value)
        self._needsSave = self._needsSave or (v != self._advertisementKey)
        self._advertisementKey = v

    @property
    def hashedAdvKey(self):
        return self._hashedKey

    @property
    def lastSeen(self):
        return self._lastSeen

    @property
    def latitude(self):
        return self._latitude

    @property
    def longitude(self):
        return self._longitude

    @property
    def status(self):
        return self._status

    @property
    def direct(self):
        return self._direct

    def updateLocation(self, when, latitude, longitude, status, direct=False):
        if self._lastSeen is None or when > self._lastSeen:
            self._longitude = longitude
            self._latitude = latitude
            self._status = status
            self._lastSeen = when
            self._direct = direct
            self._updateBatteryLevel(status)
            self._updated = True
        self._history[when] = {'lat': latitude, 'lon': longitude, 'status': status, 'direct': direct}
        self._needsSave = True

    @property
    def history(self):
        return self._history

    @property
    def imgId(self):
        return self._imgId

    @imgId.setter
    def imgId(self, value):
        self._needsSave = self._needsSave or value != self.imgId
        self._imgId = value

    @property
    def hasBatteryStatus(self):
        return self._hasBattery

    @hasBatteryStatus.setter
    def hasBatteryStatus(self, value):
        self._needsSave = self._needsSave or value != self._hasBattery
        self._hasBattery = value

    @property
    def batteryLevel(self):
        return self._batteryLevel

    @batteryLevel.setter
    def batteryLevel(self, value):
        self._needsSave = self._needsSave or value != self._batteryLevel
        self._batteryLevel = value

    @property
    def eventCountChanged(self):
        value = self._eventCountChanged
        self._eventCountChanged = False
        return value

    @property
    def notifyEvent(self):
        return self._notifyEvent

    @notifyEvent.setter
    def notifyEvent(self, value):
        self._needsSave = self._needsSave or value != self._notifyEvent
        self._notifyEvent = value

    @property
    def notifyText(self):
        return self._notifyText

    @notifyText.setter
    def notifyText(self, value):
        self._needsSave = self._needsSave or value != self._notifyText
        self._notifyText = value

    @property
    def updated(self):
        return self._updated

    @updated.setter
    def updated(self, value):
        self._needsSave = self._needsSave or value != self._updated
        self._updated = value

    def _updateBatteryLevel(self, status):
        idx = (status & 0b11000000) >> 6
        self.batteryLevel = ['full', 'medium', 'low', 'critical'][idx]
        if self._eventCount != (status & 0b00111111):
            self._eventCountChanged = True
        self._eventCount = (status & 0b00111111)

    @property
    def enableGeoFencing(self):
        return self._enableGeoFencing

    @enableGeoFencing.setter
    def enableGeoFencing(self, value):
        self._needsSave = self._needsSave or value != self._enableGeoFencing
        self._enableGeoFencing = value

    @property
    def trustedTagId(self):
        return self._trustedTagId

    @trustedTagId.setter
    def trustedTagId(self, value):
        self._needsSave = self._needsSave or value != self._trustedTagId
        self._trustedTagId = value

    @property
    def trustedLocationName(self):
        return self._trustedLocationName

    @trustedLocationName.setter
    def trustedLocationName(self, value):
        self._needsSave = self._needsSave or value != self._trustedLocationName
        self._trustedLocationName = value

    @property
    def trustedLocationLat(self):
        return self._trustedLocationLat

    @trustedLocationLat.setter
    def trustedLocationLat(self, value):
        self._needsSave = self._needsSave or value != self._trustedLocationLat
        self._trustedLocationLat = value

    @property
    def trustedLocationLon(self):
        return self._trustedLocationLon

    @trustedLocationLon.setter
    def trustedLocationLon(self, value):
        self._needsSave = self._needsSave or value != self._trustedLocationLon
        self._trustedLocationLon = value

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, value):
        self._needsSave = self._needsSave or value != self._distance
        self._distance = value

    @property
    def appleId(self):
        return self._appleId

    @appleId.setter
    def appleId(self, value):
        self._needsSave = self._needsSave or value != self._appleId
        self._appleId = value

    def checkGeoFencing(self, ctx):
        if self.enableGeoFencing == 'trustLoc':
            actDistance = calculateDistance([self.longitude, self.latitude],
                                            [self.trustedLocationLon, self._trustedLocationLat])
            if actDistance > self._distance:
                return ['alert', f"Airtag {self._name} has moved too far away from {self._trustedLocationName}. "
                                 f"Distance is {int(actDistance)}, expected was {self._distance}", actDistance]
            return ['ok', f'Airtag {self._name} is within distance ({int(actDistance)} meters)', actDistance]
        if self.enableGeoFencing == 'trustTag':
            if self._trustedTagId in ctx.airtags.keys():
                otherTag = ctx.airtags[self._trustedTagId]
                actDistance = calculateDistance([self.longitude, self.latitude],
                                                [otherTag.longitude, otherTag.latitude])
                if actDistance > self._distance:
                    return ['alert', f"Airtag <{self._name}> has moved too far away from Airtag <{otherTag.name}>. "
                                     f"Distance is {int(actDistance)} meters, expected was {int(self._distance)} meters",
                            actDistance]
                return ['ok', f'Airtag {self._name} is within distance ({int(actDistance)} meters)', actDistance]
            else:
                return ['fail',
                        f"Airtag {self._name}: Configuration problem, tag with id {self._trustedTagId} not found.", 0]
        return ['N/A', f'Airtag {self._name}: geo fencing is not configured', 0]
