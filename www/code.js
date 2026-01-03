var map;
var layer_mapnik;
var layer_tah;
var layer_markers;
var mapMarkers = [];
var lastLocationUpdate = 0;
var usedReports = 0;

function drawMap() {
    var element = document.getElementById('map');

    // Height has to be set. You can do this in CSS too.
    element.style = 'height:600px;';

    // Create Leaflet map on map element.
    map = L.map(element);

    // Add OSM tile layer to the Leaflet map.
    L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Target's GPS coordinates.
    var target = L.latLng('47.50737', '19.04611');
    var t2 = L.latLng('51.5062564', '12.3236131');

    var bounds = new L.LatLngBounds([target, t2]);

    // Set map's center to target with zoom 14.
    //map.setView(target, 14);
    map.fitBounds(bounds);

    // Place a marker on the same location.
    var m1 = L.marker(target)
    m1.addTo(map);
    var m2 = L.marker(t2)
    m2.addTo(map).bindTooltip("ML Bike",
    {
        permanent: true,
        direction: 'right'
    }
    );
    mapMarkers.push(m1);
    mapMarkers.push(m2);
    getLastLocationUpdate();
    listTags();
}

function getLastLocationUpdate() {
    var url = "/api"
    var params = { "command" : "lastLocationUpdate" };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText);
                console.log(jsn);
                lastLocationUpdate = jsn.lastLocationUpdate;
                usedReports = jsn.usedReports;
                if(jsn.firmware) {
                    divFw = document.getElementById("firmware");
                    divFw.style.display = "inline";
                }
            }
        }
    }
}

var intervalLocUpdate = window.setInterval(function(){
  let llU = document.getElementById("lastLocationUpdate");
  if(lastLocationUpdate>0) {
    const strDate = tsToDateString(lastLocationUpdate);
    const now = Date.now();
    const elapsed = (lastLocationUpdate*1000) - now;
    const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
    if (elapsed>-60000) {
        diff = formatter.format(Math.round(elapsed / 1000), 'second');
    }
    else if (elapsed>-3600000) {
        diff = formatter.format(Math.round(elapsed / 60000), 'minute');
    }
    else if (elapsed>-86400000) {
        diff = formatter.format(Math.round(elapsed / 3600000), 'hour');
    }
    else {
        diff = formatter.format(Math.round(elapsed / 86400000), 'day');
    }
    let rpts = "no new location data since previous update"
    if (usedReports>0) {
        rpts = usedReports + " update(s) since previous update"
    }
    llU.innerText = strDate + " [" + diff + " / " + rpts + "]";
  }
  else {
    llU.innerText = "never";
  }
}, 5000);

function listTags() {
    var url = "/api"
    var params = { "command" : "listTags" };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
                var element = document.getElementById('map');
                var arrLatLon = []
                for(var i = 0; i < mapMarkers.length; i++){
                    map.removeLayer(mapMarkers[i]);
                }
                mapMarkers = []
                var root = document.getElementById("contentList");
                root.innerHTML = document.getElementById("prefixAirTag").innerHTML;
                Object.keys(jsn).forEach(function(key) {
                    console.log('Key : ' + key + ', Value : ' + jsn[key])
                    console.log(jsn[key].name)
                    var html;
                    if (String(jsn[key].hasBattery).toLowerCase() === 'true') {
                        html = document.getElementById("tmplAirTag2").innerHTML;
                    } else {
                        html = document.getElementById("tmplAirTag").innerHTML;
                    }
                    var strDate = "never"
                    if (jsn[key].lastSeen) {
                        strDate = tsToDateString(jsn[key].lastSeen)
                        if(jsn[key].direct) {
                            strDate += " (mqtt)"
                        }
                        var pos = L.latLng(jsn[key].latitude, jsn[key].longitude);
                        arrLatLon.push(pos)
                        var marker = L.marker(pos)
                        marker.addTo(map).bindTooltip(jsn[key].name, {
                            permanent: true,
                            direction: 'right'
                        }
                        );
                        mapMarkers.push(marker)
                    }
                    let png = '.png';
                    if (jsn[key].updated) {
                        png = 'Bold.png';
                    }
                    root.innerHTML += html.replace(/##NAME##/g, jsn[key].name).replace(/##ID##/g, jsn[key].id)
                            .replace(/##LASTSEEN##/g, strDate).replace(/##IMGID##/g, "./" + jsn[key].imgId + png)
                            .replace(/##BATLEVEL##/g, "./battery" + jsn[key].batteryLevel + ".png");
                });
                root.style.color= "#f2f2f2";
                var bounds = new L.LatLngBounds(arrLatLon);
                map.fitBounds(bounds);
                map.invalidateSize();
            }
        }
    }
}

function submitCreds() {
    var userName = document.getElementById("userName").value;
    var password = document.getElementById("password").value;
    var url = "/api"
    var params = { "command" : "creds", "userName": userName, "password": password  };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                document.getElementById("creds").style.display = "none";
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
            }
        }
    }
}

function submitAuth() {
    var auth = document.getElementById("factorAuth").value;
    var url = "/api"
    var params = { "command" : "auth", "ndFactor": auth  };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                document.getElementById("ndFactor").style.display = "none";
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
            }
        }
    }
}

function refresh() {
    document.getElementById("errMsg").style.display = "none";
    var url = "/api"
    var params = { "command" : "refresh" };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText);
                console.log(jsn);
                getLastLocationUpdate();
                listTags();
            }
        }
    }
    signInStatus(0, Date.now())
}

function signInStatus(ts, startTime) {
    var url = "/api"
    var params = { "command" : "signInStatus", "timeStamp": ts };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
                if (jsn.status === "creds") {
                    document.getElementById("creds").style.display = "block";
                    startTime = Date.now();
                }
                if (jsn.status === "auth") {
                    document.getElementById("ndFactor").style.display = "block";
                    startTime = Date.now();
                }
                if (jsn.status === "fail") {
                    document.getElementById("errMsg").innerHTML = jsn.msg;
                    document.getElementById("errMsg").style.display = "block";
                }
                if (jsn.status !== "done" && jsn.status !== "fail") {
                    now = Date.now();
                    elapsed = (now - startTime) / 1000;
                    if (elapsed < 180) {
                        signInStatus(jsn.timeStamp, startTime);
                    }
                }
            }
        }
    }
}

function showAbout() {
    document.getElementById("aboutArea").style.display = 'block';
    document.getElementById("rightMap").style.display = 'none';
    document.getElementById("rightTagEditor").style.display = 'none';
}

function hideAbout() {
    document.getElementById("aboutArea").style.display = 'none';
    document.getElementById("rightMap").style.display = 'block';
}

function editTag(id) {
    var url = "/api"
    var params = { "command" : "getTagData", "id": id };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
                document.getElementById("tagName").value = jsn.name;
                document.getElementById("privKey").value = jsn.privateKey;
                document.getElementById("advKey").value = jsn.advertisementKey;
                document.getElementById("batStatus").checked = jsn.hasBattery;
                document.getElementById("notifyEvent").checked = jsn.notifyEvent;
                document.getElementById("notifyText").value = jsn.notifyText;
                document.getElementById("distance").value = jsn.distance;
                document.getElementById("latitude").value = "";
                document.getElementById("longitude").value = "";
                if (jsn.enableGeoFencing === 'disable') {
                    document.getElementById('disable').checked = true;
                    gfHideAll();
                }
                if (jsn.enableGeoFencing === 'trustLoc') {
                    document.getElementById('trustedLocation').checked = true;
                    document.getElementById("locName").value = jsn.trustedLocationName
                    document.getElementById("latitude").value = jsn.latitude;
                    document.getElementById("longitude").value = jsn.longitude;
                    gfShowLoc();
                }
                if (jsn.enableGeoFencing === 'trustTag') {
                    document.getElementById('trustedTag').checked = true;
                    gfShowTag(jsn.trustedTagId);
                }
                if (jsn.hasOwnProperty("imgId")) {
                    markImg(jsn["imgId"]);
                }
                else {
                    markImg("airtag");
                }
            }
        }
    }
    document.getElementById("cmd").value = "editTag";
    document.getElementById("id").value= id
    document.getElementById("rightTagEditor").style.display = 'block';
    document.getElementById("rightMap").style.display = 'none';
}

function generateKeys() {
    var url = "/api"
    var params = { "command" : "generateKeys"};
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
                document.getElementById("tagName").value = jsn.name;
                document.getElementById("privKey").value = jsn.privateKey;
                document.getElementById("advKey").value = jsn.advertisementKey;
            }
        }
    }
}

function downloadFirmware() {
    document.getElementById("divErrFirmware").style.display = "none";
    var url = "/api"
    var id = document.getElementById("id").value;
    var advertisementKey = document.getElementById("advKey").value;
    var params = { "command" : "firmware", "id": id, "advertisementKey": advertisementKey};
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
                if (jsn.createdKey) {
                    document.getElementById("privKey").value = jsn.privateKey;
                    document.getElementById("advKey").value = jsn.advertisementKey;
                }
                if (jsn.status=="ok") {
                    downloadFirmware2(jsn.name);
                }
                else {
                    let errMsg = document.getElementById("txtErrFirmware");
                    errMsg.innerHTML = jsn.errMsg;
                    document.getElementById("divErrFirmware").style.display = "block";
                }
            }
        }
    }
}

function downloadFirmware2(name) {
    document.getElementById("divErrFirmware").style.display = "none";
    var url = "/download"
    var params = { "name" : name};
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.responseType = 'blob';
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var blob = http.response;
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = name;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
            }
        }
    }
}

function loadHistory(id) {
    var url = "/api"
    var params = { "command" : "history", "id": id };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText);
                console.log(jsn);
                var element = document.getElementById('map');
                var arrLatLon = []
                for(var i = 0; i < mapMarkers.length; i++){
                    map.removeLayer(mapMarkers[i]);
                }
                mapMarkers = []
                Object.keys(jsn.history).forEach(function(key) {
                    var pos = L.latLng(jsn.history[key].lat, jsn.history[key].lon);
                    arrLatLon.push(pos)
                })
                var marker = L.marker(arrLatLon[0]);
                marker.addTo(map).bindTooltip(jsn.name, {
                            permanent: true,
                            direction: 'right'
                        }
                    );
                mapMarkers.push(marker)

                var path = L.polyline(
                    arrLatLon,
                    {"delay":400,"dashArray":[10,20],"weight":5,"color":"black","paused":true,"reverse":false}
                    ).addTo(map);
                map.addLayer(path);
                map.fitBounds(path.getBounds());
                mapMarkers.push(path);
                element = document.getElementById('back');
                element.style.display = 'block';
            }
        }
    }
}

function backToNormal() {
    var element = document.getElementById('back');
    element.style.display = 'none';
    listTags();
}

function addTag() {
    document.getElementById("tagName").value = "";
    document.getElementById("privKey").value = "";
    document.getElementById("advKey").value = "";
    document.getElementById("cmd").value = "addTag";
    document.getElementById("id").value= id
    document.getElementById("rightTagEditor").style.display = 'block';
    document.getElementById("rightMap").style.display = 'none';
    document.getElementById("hasBatStatus").checked = false;
    document.getElementById("notifyEvent").checked = false;
    document.getElementById("notifyText").value = "";
    document.getElementById("disable").checked = false;
    document.getElementById("distance").value = "100";
    gfHideAll();
    markImg('airtag');
}

function markImg(imgName) {
    document.getElementById("imgId").value = imgName
    const imgs = ['airtag', 'backpack', 'bike', 'keys', 'suitcase', 'safe', 'tool', 'mailbox'];
    let src;
    imgs.forEach(function(element) {
        let img = document.getElementById(element);
        if (imgName === element) {
            src = "./" + element + "Bold.png";
        }
        else {
            src = "./" + element + ".png";
        }
        img.src = src;
    });
}

function saveTagEdit() {
    var fldName = document.getElementById("tagName").value;
    var privKey = document.getElementById("privKey").value;
    var advKey = document.getElementById("advKey").value;
    var cmd = document.getElementById("cmd").value;
    var id = document.getElementById("id").value;
    var imgId = document.getElementById("imgId").value;
    var hasBatStatus = document.getElementById("batStatus").checked;
    var enableGeoFencing = document.querySelector('input[name = geoFencing]:checked').value;
    var distance = document.getElementById("distance").value;
    var trustedLocationName = document.getElementById("locName").value;
    var latitude = document.getElementById("latitude").value;
    var longitude = document.getElementById("longitude").value;
    var notifyEvent = document.getElementById("notifyEvent").checked;
    var notifyText = document.getElementById("notifyText").value;
    var trustedTagId = "";
    let tmp =  document.querySelector('input[name = trustedTag]:checked');
    if (tmp) {
        trustedTagId = tmp.value;
    }

    if (latitude && latitude.includes(', ')) {
        var splt = latitude.split(', ');
        latitude = splt[0];
        longitude = splt[1];
        document.getElementById("latitude").value = latitude;
        document.getElementById("longitude").value = longitude;
    }

    document.getElementById("divErrLocName").style.display='none';
    document.getElementById("divErrDistance").style.display='none';
    document.getElementById("divErrLatitude").style.display='none';
    document.getElementById("divErrLongitude").style.display='none';
    document.getElementById("divErrTagId").style.display='none';
    var validated = true;
    if (enableGeoFencing === "trustLoc") {
        if (!trustedLocationName) {
            document.getElementById("divErrLocName").style.display='block';
            validated = false;
        }
        if (!Number.isInteger(Number(distance)) || distance.valueOf()<100) {
            document.getElementById("divErrDistance").style.display='block';
            validated = false;
        }
        if (!isFinite(latitude)) {
            document.getElementById("divErrLatitude").style.display='block';
            validated = false;
        }
        if (!isFinite(longitude)) {
            document.getElementById("divErrLongitude").style.display='block';
            validated = false;
        }
    }
    if (enableGeoFencing === "trustTag") {
        if (!trustedTagId) {
            document.getElementById("divErrTagId").style.display='block';
            validated = false;
        }
    }
    if (!validated) {
        return;
    }

    var url = "/api"
    var params = { "command" : cmd, "name": fldName, "privateKey": privKey, "advertisementKey": advKey, "id": id,
                "imgId": imgId, 'hasBatteryStatus': hasBatStatus, 'enableGeoFencing': enableGeoFencing,
                'trustedLocationName': trustedLocationName, 'distance': Number(distance),
                'latitude': Number(latitude), 'longitude': Number(longitude), 'trustedTagId': trustedTagId,
                 'notifyEvent': notifyEvent, 'notifyText': notifyText};
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText);
                console.log(jsn);
                listTags();
            }
        }
    }

    cancelTagEdit();
}

function cancelTagEdit() {
    document.getElementById("rightTagEditor").style.display = 'none';
    document.getElementById("rightMap").style.display = 'block';
    document.getElementById("divErrLocName").style.display = 'none';
    document.getElementById("divErrDistance").style.display='none';
    document.getElementById("divErrLatitude").style.display='none';
    document.getElementById("divErrLongitude").style.display='none';
    document.getElementById("divErrTagId").style.display='none';
}

//
// https://stackoverflow.com/questions/8064691/how-do-i-pass-along-variables-with-xmlhttprequest
//
function formatParams( params ){
  return "?" + Object
        .keys(params)
        .map(function(key){
          return key+"="+encodeURIComponent(params[key])
        })
        .join("&")
}

function tsToDateString(ts) {
    var date = new Date(ts * 1000);
    //var year = date.getFullYear()
    //var month = "0" + (date.getMonth()+1)
    //var day = "0" + date.getDate()
    //var hours = "0" + date.getHours();
    //var minutes = "0" + date.getMinutes();
    //var seconds = "0" + date.getSeconds();
    //return hours.substr(-2) + ':' + minutes.substr(-2) + ':' + seconds.substr(-2) + " " + day.substr(-2) + "." + month.substr(-2) + "." + year;
    return date.toLocaleString();
}

function gfHideAll() {
    document.getElementById("divDistance").style.display = 'none';
    document.getElementById("divLoc").style.display = 'none';
    var dvTag = document.getElementById("divTag")
    dvTag.innerHTML = '';
    dvTag.style.display = 'none';
}

function gfShowLoc() {
    document.getElementById("divDistance").style.display = 'block';
    document.getElementById("divLoc").style.display = 'block';
    var dvTag = document.getElementById("divTag")
    dvTag.innerHTML = '';
    dvTag.style.display = 'none';
}

function gfShowTag(tagId) {
    document.getElementById("divDistance").style.display = 'block';
    document.getElementById("divLoc").style.display = 'none';
    var dvTag = document.getElementById("divTag");
    var html = document.getElementById("tmplgfTag").innerHTML;
    var url = "/api"
    var params = { "command" : "listTags" };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    dvTag.innerHTML = "";
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
                Object.keys(jsn).forEach(function(key) {
                    console.log('Key : ' + key + ', Value : ' + jsn[key]);
                    console.log(jsn[key].name);
                    dvTag.innerHTML += html.replace(/##NAME##/g, jsn[key].name).replace(/##ID##/g, jsn[key].id);
                });
                if (tagId) {
                    document.getElementById(tagId).checked = true
                }
                dvTag.style.display = 'block';
            }
        }
    }
}