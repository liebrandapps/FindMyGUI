var map;
var layer_mapnik;
var layer_tah;
var layer_markers;
var mapMarkers = [];

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
                let strDate = "never";
                let diff;
                if (jsn.lastLocationUpdate > 0) {
                    strDate = tsToDateString(jsn.lastLocationUpdate);
                    const now = Date.now();
                    const elapsed = (jsn.lastLocationUpdate*1000) - now;
                    console.log(elapsed);
                    const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
                    if (elapsed>-60000) {
                        diff = formatter.format(Math.round(elapsed / 1000), 'second');
                    }
                    else if (elapsed>-3600000) {
                        diff = formatter.format(Math.round(elapsed / 60000), 'minute');
                    }
                    else if (elapsed>-86400000) {
                        diff = formatter.format(Math.round(dielapsedff / 3600000), 'hour');
                    }
                    else {
                        diff = formatter.format(Math.round(elapsed / 86400000), 'day');
                    }
                 }
                document.getElementById("lastLocationUpdate").innerText = strDate + " (" + diff + ")";
            }
        }
    }
}

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
                    var html = document.getElementById("tmplAirTag").innerHTML;
                    var strDate = "never"
                    if (jsn[key].lastSeen) {
                        strDate = tsToDateString(jsn[key].lastSeen)
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
                    root.innerHTML += html.replace(/##NAME##/g, jsn[key].name).replace(/##ID##/g, jsn[key].id)
                            .replace(/##LASTSEEN##/g, strDate);
                })
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
                }
                if (jsn.status === "factor") {
                    document.getElementById("ndFactor").style.display = "block";
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
            }
        }
    }
    document.getElementById("cmd").value = "editTag";
    document.getElementById("id").value= id
    document.getElementById("rightTagEditor").style.display = 'block';
    document.getElementById("rightMap").style.display = 'none';
}

function addTag() {
    document.getElementById("tagName").value = "";
    document.getElementById("privKey").value = "";
    document.getElementById("advKey").value = "";
    document.getElementById("cmd").value = "addTag";
    document.getElementById("id").value= id
    document.getElementById("rightTagEditor").style.display = 'block';
    document.getElementById("rightMap").style.display = 'none';
}


function saveTagEdit() {
    var fldName = document.getElementById("tagName").value;
    var privKey = document.getElementById("privKey").value;
    var advKey = document.getElementById("advKey").value;
    var cmd = document.getElementById("cmd").value;
    var id = document.getElementById("id").value;
    var url = "/api"
    var params = { "command" : cmd, "name": fldName, "privateKey": privKey, "advertisementKey": advKey, "id": id};
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
    console.log(date)
    var year = date.getFullYear()
    var month = "0" + (date.getMonth()+1)
    var day = "0" + date.getDate()
    var hours = "0" + date.getHours();
    var minutes = "0" + date.getMinutes();
    var seconds = "0" + date.getSeconds();
    return hours.substr(-2) + ':' + minutes.substr(-2) + ':' + seconds.substr(-2) + " " + day.substr(-2) + "." + month.substr(-2) + "." + year;
}