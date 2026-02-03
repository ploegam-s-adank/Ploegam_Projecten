import requests, time, json

class AGOL:
    def __init__(self, username, password, portal='https://www.arcgis.com'):
        self.username = username
        self.password = password
        self.portal = portal.rstrip('/')
        self._token = None
        self._tok_expires = 0

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
            raise RuntimeError('Failed to get token: ' + str(js))

        self._token = js['token']
        self._tok_expires = t + 3600
        return self._token

    def get(self, url, params=None):
        tok = self._ensure_token()
        p = params.copy() if params else {}
        p.update({'f': 'json', 'token': tok})
        r = requests.get(url, params=p, timeout=60)
        r.raise_for_status()
        js = r.json()
        if 'error' in js:
            raise RuntimeError(str(js['error']))
        return js

    def post(self, url, data):
        tok = self._ensure_token()
        d = data.copy()
        d.update({'f': 'json', 'token': tok})
        r = requests.post(url, data=d, timeout=60)
        r.raise_for_status()
        js = r.json()
        if 'error' in js:
            raise RuntimeError(str(js['error']))
        return js

    def query(self, layer_url, where='1=1', out_fields='*', return_geometry=True):
        return self.get(
            layer_url.rstrip('/') + '/query',
            {
                'where': where,
                'outFields': out_fields,
                'returnGeometry': 'true' if return_geometry else 'false'
            }
        )

def arcgis_polygon_from_geojson(gj_geom, wkid=4326):
    """Converteert een GeoJSON-polygon of multipolygon naar een ArcGIS geometry dict."""
    typ = gj_geom.get("type")

    if typ == "Polygon":
        rings = gj_geom["coordinates"]

    elif typ == "MultiPolygon":
        rings = []
        for poly in gj_geom["coordinates"]:
            rings.extend(poly)

    else:
        raise ValueError("Geometry must be Polygon of MultiPolygon")

    return {
        "rings": rings,
        "spatialReference": {"wkid": wkid}
    }
