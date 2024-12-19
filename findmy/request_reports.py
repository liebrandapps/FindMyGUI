import base64
import datetime
import hashlib
import json
import os
import struct

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from findmy.pypush_gsa_icloud import icloud_login_mobileme, generate_anisette_headers


class FindMy:

    def __init__(self, ctx):
        self.ctx = ctx

    def sha256(self, data):
        digest = hashlib.new("sha256")
        digest.update(data)
        return digest.digest()

    def decrypt(self, enc_data, algorithm_dkey, mode):
        decryptor = Cipher(algorithm_dkey, mode, default_backend()).decryptor()
        return decryptor.update(enc_data) + decryptor.finalize()

    def decode_tag(self, data):
        latitude = struct.unpack(">i", data[0:4])[0] / 10000000.0
        longitude = struct.unpack(">i", data[4:8])[0] / 10000000.0
        confidence = int.from_bytes(data[8:9], 'big')
        status = int.from_bytes(data[9:10], 'big')
        return {'lat': latitude, 'lon': longitude, 'conf': confidence, 'status': status}

    def getAuth(self, regenerate=False, second_factor='sms'):
        CONFIG_PATH =  "./data/auth.json"
        if os.path.exists(CONFIG_PATH) and not regenerate:
            with open(CONFIG_PATH, "r") as f:
                j = json.load(f)
        else:
            mobileme = None
            try:
                mobileme = icloud_login_mobileme(self.ctx, second_factor=second_factor)
            except requests.exceptions.ConnectionError as e:
                msg = f"[ICLOUD] Anisette Server not running: {str(e)}"
                self.ctx.errMsg = msg
                self.ctx.log.error(msg)
            if mobileme is None:
                return None
            j = {'dsid': mobileme['dsid'],
                 'searchPartyToken': mobileme['delegates']['com.apple.mobileme']['service-data']['tokens'][
                     'searchPartyToken']}
            with open(CONFIG_PATH, "w") as f:
                json.dump(j, f)
        return (j['dsid'], j['searchPartyToken'])

    def retrieveLocations(self, usePrevAuth=True):
        privkeys = {}
        names = {}
        for tag in self.ctx.airtags.values():
            hashedKey = tag.hashedAdvKey
            privkeys[hashedKey] = tag.privateKey
            names[hashedKey] = tag.name
            tag.updated = False

        unixEpoch = int(datetime.datetime.now().strftime('%s'))
        if self.ctx.lastLocationUpdate > 0:  # (unixEpoch - (60 * 60 * 144)):
            startdate = self.ctx.lastLocationUpdate
        else:
            startdate = unixEpoch - (60 * 60 * 48)

        self.ctx.log.info(f"[LOC RETR] Time window for query is " +
                          f"{datetime.datetime.fromtimestamp(startdate).strftime( '%Y-%m-%d %H:%M:%S')} to " +
                          f"{datetime.datetime.fromtimestamp(unixEpoch).strftime('%Y-%m-%d %H:%M:%S')}")

        auth = self.getAuth(regenerate=not (usePrevAuth),
                            second_factor='trusted_device' if self.ctx.cfg.appleId_trustedDevice else 'sms')
        if auth is None:
            return
        queue = list(names.keys())
        chunk = []
        res = []
        while len(queue) > 0:
            chunk.append(queue.pop(0))
            if len(chunk) == 5 or len(queue) == 0:
                data = {
                    "search": [{"startDate": startdate * 1000, "endDate": unixEpoch * 1000, "ids": chunk}]}
                r = requests.post("https://gateway.icloud.com/acsnservice/fetch",
                                  auth=auth,
                                  headers=generate_anisette_headers(
                                      self.ctx.cfg.general_anisetteHost + ":" + str(self.ctx.cfg.general_anisettePort)),
                                  json=data)
                if r.status_code == 401:
                    if not (usePrevAuth):
                        self.ctx.log.error("[iCloud] Anisette is not accepting auth, GIVING UP")
                        return
                    else:
                        self.ctx.log.warn("[iCloud] Anisette is not accepting auth, trying to request PW")
                        self.retrieveLocations(False)

                res.extend(json.loads(r.content.decode())['results'])
                self.ctx.log.info(f'{r.status_code}: {len(res)} reports received.')
                chunk = []

        ordered = []
        found = set()
        for report in res:
            priv = int.from_bytes(base64.b64decode(privkeys[report['id']]), 'big')
            data = base64.b64decode(report['payload'])

            # the following is all copied from https://github.com/hatomist/openhaystack-python, thanks @hatomist!
            timestamp = int.from_bytes(data[0:4], 'big') + 978307200
            if timestamp >= startdate:
                adj = len(data) - 88
                try:
                    eph_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP224R1(), data[5+adj:62+adj])
                except ValueError as e:
                    self.ctx.log.warn(e)
                    continue
                shared_key = ec.derive_private_key(priv, ec.SECP224R1(), default_backend()).exchange(ec.ECDH(), eph_key)
                symmetric_key = self.sha256(shared_key + b'\x00\x00\x00\x01' + data[5+adj:62+adj])
                decryption_key = symmetric_key[:16]
                iv = symmetric_key[16:]
                enc_data = data[62+adj:72+adj]
                tag = data[72+adj:]

                decrypted = self.decrypt(enc_data, algorithms.AES(decryption_key), modes.GCM(iv, tag))
                tag = self.decode_tag(decrypted)
                tag['timestamp'] = timestamp
                tag['isodatetime'] = datetime.datetime.fromtimestamp(timestamp).isoformat()
                tag['key'] = names[report['id']]
                tag['goog'] = 'https://maps.google.com/maps?q=' + str(tag['lat']) + ',' + str(tag['lon'])
                for t in self.ctx.airtags.values():
                    if report['id'] == t.hashedAdvKey:
                        t.updateLocation(timestamp, tag['lat'], tag['lon'], tag['status'])
                found.add(tag['key'])
                ordered.append(tag)
        self.ctx.log.info(f'{len(ordered)} reports used.')
        ordered.sort(key=lambda item: item.get('timestamp'))
        for rep in ordered: print(rep)
        for t in self.ctx.airtags.values():
            if t.needsSave:
                t.save()
        self.ctx.log.info(f'found:   {list(found)}')
        self.ctx.log.info(f'missing: {[key for key in names.values() if key not in found]}')
        self.ctx.signInDone = True
        self.ctx.usedReports = len(ordered)
        self.ctx.lastLocationUpdate = int(datetime.datetime.now().timestamp())
