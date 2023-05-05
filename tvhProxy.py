from gevent import monkey; monkey.patch_all()

import time
import os
import requests
from gevent.pywsgi import WSGIServer
from flask import Flask, Response, request, jsonify, abort, render_template

app = Flask(__name__)

# URL format: <protocol>://<username>:<password>@<hostname>:<port>, example: https://test:1234@localhost:9981
config = {
    'bindAddr': os.environ.get('TVH_BINDADDR') or '',
    'tvhUser': os.environ.get('TVH_USER') or 'test',
    'tvhPass':  os.environ.get('TVH_PASS') or 'test',
    'tvhIP':  os.environ.get('TVH_IP') or 'localhost',
    'tvhPort':  os.environ.get('TVH_PORT') or '9981',
    'tvhProxyIP': os.environ.get('TVH_PROXY_IP') or 'localhost',
    'tvhProxyPort': os.environ.get('TVH_PROXY_PORT') or '5004',
    'tunerCount': os.environ.get('TVH_TUNER_COUNT') or 6,  # number of tuners in tvh
    'tvhWeight': os.environ.get('TVH_WEIGHT') or 300,  # subscription priority
    'chunkSize': os.environ.get('TVH_CHUNK_SIZE') or 1024*1024,  # usually you don't need to edit this
    'streamProfile': os.environ.get('TVH_PROFILE') or 'pass'  # specifiy a stream profile that you want to use for adhoc transcoding in tvh, e.g. mp4
}

discoverData = {
    'FriendlyName': 'tvhProxy',
    'Manufacturer' : 'Silicondust',
    'ModelNumber': 'HDTC-2US',
    'FirmwareName': 'hdhomeruntc_atsc',
    'TunerCount': int(config['tunerCount']),
    'FirmwareVersion': '20150826',
    'DeviceID': '12345678',
    'DeviceAuth': 'test1234',
    'BaseURL': 'http://%s:%s' % (config['tvhProxyIP'], config['tvhProxyPort']),
    'LineupURL': 'http://%s:%s/lineup.json' % (config['tvhProxyIP'], config['tvhProxyPort'])
}

@app.route('/discover.json')
def discover():
    return jsonify(discoverData)


@app.route('/lineup_status.json')
def status():
    return jsonify({
        'ScanInProgress': 0,
        'ScanPossible': 1,
        'Source': "Cable",
        'SourceList': ['Cable']
    })


@app.route('/lineup.json')
def lineup():
    lineup = []

    for c in _get_channels():
        if c['enabled']:
            url = 'http://%s:%s@%s:%s/stream/channel/%s?profile=%s&weight=%s' % (config['tvhUser'], config['tvhPass'], config['tvhIP'], config['tvhPort'], c['uuid'], config['streamProfile'], int(config['tvhWeight']))
            lineup.append({'GuideNumber': str(c['number']),
                           'GuideName': c['name'],
                           'URL': url
                           })

    return jsonify(lineup)


@app.route('/lineup.post', methods=['GET', 'POST'])
def lineup_post():
    return ''

@app.route('/')
@app.route('/device.xml')
def device():
    return render_template('device.xml',data = discoverData),{'Content-Type': 'application/xml'}

def _get_channels():
    url = 'http://%s:%s/api/channel/grid?start=0&limit=999999' % (config['tvhIP'], config['tvhPort']) 
    try:
        r = requests.get(url, auth=requests.auth.HTTPDigestAuth(config['tvhUser'], config['tvhPass']))
        return r.json()['entries']

    except Exception as e:
        print('An error occured: ' + repr(e))

if __name__ == '__main__':
    http = WSGIServer((config['bindAddr'], int(config['tvhProxyPort'])), app.wsgi_app)
    http.serve_forever()
