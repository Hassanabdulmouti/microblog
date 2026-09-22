"""Check the local app -> Prometheus -> Grafana/Alertmanager -> webhook flow."""
import base64
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GRAFANA = 'http://127.0.0.1:3004/grafana'
PROMETHEUS = 'http://127.0.0.1:9094'
AUTH = base64.b64encode(b'admin:local-monitoring-demo').decode()


def request(url, auth=False):
    headers = {'Authorization': 'Basic ' + AUTH} if auth else {}
    with urlopen(Request(url, headers=headers), timeout=5) as response:
        return json.load(response)


def query(expression):
    return request(PROMETHEUS + '/api/v1/query?' + urlencode({'query': expression}))['data']['result']


def wait_for(description, check, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                print('PASS:', description, flush=True)
                return result
        except (URLError, KeyError, ValueError, IndexError):
            pass
        time.sleep(2)
    raise AssertionError('Timed out: ' + description)


wait_for('application database is healthy',
         lambda: request('http://127.0.0.1:5004/health')['status'] == 'healthy')
wait_for('Prometheus scrapes the application',
         lambda: query('up{job="microblog"}')[0]['value'][1] == '1')
for uid in ['microblog-application', 'microblog-infrastructure']:
    dashboard = wait_for('Grafana dashboard ' + uid,
                         lambda: request(GRAFANA + '/api/dashboards/uid/' + uid, auth=True))
    assert len(dashboard['dashboard']['panels']) >= 4
source = request(GRAFANA + '/api/datasources/uid/prometheus', auth=True)
assert source['type'] == 'prometheus'
print('PASS: dashboards use the provisioned Prometheus datasource', flush=True)

selector = 'microblog_errors_total{job="microblog",endpoint="main.trigger_error"}'
baseline = wait_for('error counter has been scraped before the test', lambda: query(selector))
webhooks_before = len(request('http://127.0.0.1:8084'))
before = float(baseline[0]['value'][1])
try:
    urlopen('http://127.0.0.1:5004/debug/error', timeout=5)
except HTTPError as error:
    assert error.code == 500
else:
    raise AssertionError('The demonstration endpoint did not return HTTP 500')
print('PASS: intentional HTTP 500 generated', flush=True)
wait_for('Prometheus captured the new error',
         lambda: float(query(selector)[0]['value'][1]) > before)
wait_for('MicroblogApplicationError is firing',
         lambda: query('ALERTS{alertname="MicroblogApplicationError",alertstate="firing"}'))
wait_for('Alertmanager delivered the error to the local webhook',
         lambda: any(event.get('status') == 'firing' and any(
             alert['labels'].get('alertname') == 'MicroblogApplicationError'
             for alert in event.get('alerts', []))
             for event in request('http://127.0.0.1:8084')[webhooks_before:]))
# Query through Grafana's datasource proxy, proving Grafana can read the data.
wait_for('Grafana can query the captured error',
         lambda: request(GRAFANA + '/api/datasources/proxy/uid/prometheus/api/v1/query?' +
                         urlencode({'query': selector}), auth=True)['data']['result'])
print('All local monitoring checks passed. Production webhook.site delivery is a separate deployment check.')
