import requests, time, json

class AGOL:
    def __init__(self, username, password, portal='https://www.arcgis.com'):
        self.username = username
        self.password = password
        self.portal = portal.rstrip('/')
        self._token = None
        self._tok_expires = 0

    # ----------------------------------------------------------------------
    # Token
    # ----------------------------------------------------------------------
    def _ensure_token(self):
        t = int(time.time())
        if self._token and t < self._tok_expires - 60:
            return self._token

        url = self.portal + '/sharing/rest/generateToken'
        data = {
            'f': 'json',
            'username': self.username,
            'password': self.password,
            'referer': 'https://www.arcgis.com',
            'expiration': 60
        }
        r = requests.post(url, data=data, timeout=30)
        r.raise_for_status()
        js = r.json()
        if 'token' not in js:
            raise RuntimeError(js)
        self._token = js['token']
        self._tok_expires = t + 3600

        return self._token

    # ----------------------------------------------------------------------
    # Generic GET/POST
    # ----------------------------------------------------------------------
    def get(self, url, params=None):
        tok = self._ensure_token()
        p = params.copy() if params else {}
        p.update({'f': 'json', 'token': tok})
        r = requests.get(url, params=p, timeout=60)
        r.raise_for_status()
        js = r.json()
        if 'error' in js:
            raise RuntimeError(js['error'])
        return js

    def post(self, url, data):
        tok = self._ensure_token()
        d = data.copy()
        d.update({'f': 'json', 'token': tok})
        r = requests.post(url, data=d, timeout=60)
        r.raise_for_status()
        js = r.json()
        if 'error' in js:
            raise RuntimeError(js['error'])
        return js

    # ----------------------------------------------------------------------
    # Query
    # ----------------------------------------------------------------------
    def query(self, layer_url, where='1=1', out_fields='*', return_geometry=True, extra=None):
        params = {
            'where': where,
            'outFields': out_fields,
            'returnGeometry': 'true' if return_geometry else 'false'
        }
        if extra:
            params.update(extra)
        return self.get(layer_url.rstrip('/') + '/query', params)

    # ----------------------------------------------------------------------
    # Native ArcGIS REST applyEdits (preferred)
    # ----------------------------------------------------------------------
    def apply_edits(self, layer_url, adds=None, updates=None, deletes=None):
        payload = {}
        if adds:
            payload['adds'] = json.dumps(adds)
        if updates:
            payload['updates'] = json.dumps(updates)
        if deletes:
            payload['deletes'] = deletes  # is a string "1,2,3"

        return self.post(layer_url.rstrip('/') + '/applyEdits', payload)

    # ----------------------------------------------------------------------
    # Legacy wrappers (still compatible)
    # ----------------------------------------------------------------------
    def add_features(self, layer_url, features):
        return self.post(layer_url.rstrip('/') + '/addFeatures',
                         {'features': json.dumps(features)})

    def update_features(self, layer_url, features):
        return self.post(layer_url.rstrip('/') + '/updateFeatures',
                         {'features': json.dumps(features)})

    def delete_features(self, layer_url, where):
        return self.post(layer_url.rstrip('/') + '/deleteFeatures',
                         {'where': where})
