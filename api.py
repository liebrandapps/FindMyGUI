"""
  Mark Liebrand 2024
  This file is part of FindMyGUI which is released under the Apache 2.0 License
  See file LICENSE or go to for full license details https://github.com/liebrandapps/FindMyGUI
"""
import json
import time

import requests.exceptions

from airTag import AirTag
from findmy.request_reports import FindMy


class API:

    def __init__(self, ctx):
        self.ctx = ctx
        self.log = ctx.log

    def call(self, cmd, params=None):
        self.log.debug(f"[API] Handling API command <{cmd}>")
        result = {}
        if cmd == "listTags":
            result = self._listTags()
        if cmd == 'getPos':
            result = self._getPos()
        if cmd == 'refresh':
            result = self._refresh()
        if cmd == 'getTagData':
            result = self._getTagData(params['id'][0])
        if cmd == 'editTag':
            result = self._editTag(params['id'][0], params['name'][0], params['privateKey'][0],
                                   params['advertisementKey'][0], params['imgId'][0])
        if cmd == 'addTag':
            result = self._addTag(params['id'][0], params['name'][0], params['privateKey'][0],
                                  params['advertisementKey'][0], params['imgId'][0])
        if cmd == 'signInStatus':
            result = self._signInStatus(int(params['timeStamp'][0]))
        if cmd == 'creds':
            result = self._creds(params['userName'][0], params['password'][0])
        if cmd == 'auth':
            result = self._auth(params['ndFactor'][0])
        if cmd == 'lastLocationUpdate':
            result = self._lastLocationUpdate()
        if cmd == 'history':
            result = self._history(params['id'][0])
        return json.dumps(result if result is not None else {})

    def _listTags(self):
        dct = {}
        for id in self.ctx.airtags.keys():
            dct[id] = self.ctx.airtags[id].toDict()
        return dct

    def _getPos(self):
        findMy = FindMy(self.ctx)
        data = findMy.retrieveLocations()
        return data

    def _refresh(self):
        self.ctx.signInDone = False
        findMy = FindMy(self.ctx)
        try:
            data = findMy.retrieveLocations()
        except requests.exceptions.ConnectTimeout as e:
            msg = f"[API] Anisette Server not running: {str(e)}"
            self.ctx.errMsg = msg
            self.ctx.log.error(msg)
            data = {"status": "fail", "msg": msg}
        return data

    def _getTagData(self, id):
        self.log.debug(f"[API] Cmds' getTagData parameter is id={id}")
        if id in self.ctx.airtags.keys():
            tag = self.ctx.airtags[id]
            dct = tag.toDict()
            dct['status'] = 'ok'
        else:
            dct = {'status': 'fail', 'msg': 'tag not found', 'id': id}
        return dct

    def _editTag(self, id, name, privKey, advKey, imgId):
        self.log.debug(f"[API] Cmds' editTag parameter are id={id}, name={name}, private Key={privKey}, "
                       f"advertisementKey={advKey}")
        if id in self.ctx.airtags.keys():
            tag = self.ctx.airtags[id]
            tag.name = name
            tag.privateKey = privKey
            tag.advertisementKey = advKey
            tag.imgId = imgId
            if tag.needsSave:
                tag.save()
            dct = {'status': 'ok', 'dataChanged': str(tag.needsSave)}
        else:
            dct = {'status': 'fail', 'msg': 'tag not found', 'id': id}
        return dct

    def _addTag(self, id, name, privKey, advKey, imgId):
        self.log.debug(f"[API] Cmds' addTag parameter are id={id}, name={name}, private Key={privKey}, "
                       f"advertisementKey={advKey}")
        tag = AirTag(self.ctx)
        tag.name = name
        tag.privateKey = privKey
        tag.advertisementKey = advKey
        tag.imgId = imgId
        tag.save()
        self.ctx.airtags[tag.id] = tag
        return {'status': 'ok', 'id': tag.id}

    def _signInStatus(self, timeStamp):
        self.log.debug(f"[API] Cmds' signInStatus parameter is timeStamp={timeStamp}")
        dct = {'status': 'wait', 'timeStamp': timeStamp}
        idx = 3
        while idx > 0:
            if self.ctx.signInDone:
                dct['status'] = "done"
                self.ctx.signInDone = False
                break
            elif len(self.ctx.errMsg) > 0:
                dct['status'] = "fail"
                dct['msg'] = self.ctx.errMsg
                self.ctx.errMsg = ""
                break
            elif self.ctx.requestCreds > timeStamp:
                dct['status'] = "creds"
                dct['timeStamp'] = self.ctx.requestCreds
                break
            elif self.ctx.requestAuth > timeStamp:
                dct['status'] = "auth"
                dct['timeStamp'] = self.ctx.requestAuth
                break
            idx -= 1
            time.sleep(1.0)
        return dct

    def _creds(self, userName, password):
        self.log.debug(f"[API] Cmds' creds parameter are userName={userName}, password=(is set: {len(password) > 0})")
        self.ctx.userName = userName
        self.ctx.password = password
        return {'status': 'ok'}

    def _auth(self, ndFactor):
        self.log.debug(f"[API] Cmds' auth parameter are ndFactor={ndFactor}")
        self.ctx.ndFactor = str(ndFactor)
        return {'status': 'ok'}

    def _lastLocationUpdate(self):
        return {'lastLocationUpdate': self.ctx.lastLocationUpdate}

    def _history(self, tagId):
        self.log.debug(f"[API] Cmds' history parameter is id={tagId}")
        dct = {}
        if tagId in self.ctx.airtags.keys():
            tag = self.ctx.airtags[tagId]
            dct['status'] = 'ok'
            dct['history'] = tag.history
            dct['name'] = tag.name
        else:
            dct['status'] = 'fail'
            dct['msg'] = f"AirTag with id {tagId} not found."
        return dct