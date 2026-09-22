"""Verify public HTTPS, Grafana metrics and a new webhook.site alert."""
import base64
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
settings = json.loads((ROOT / 'ansible/kmom04.private.yml').read_text())
BASE = 'https://' + settings['domain_name']
AUTH = base64.b64encode(('reviewer' + ':' +
                         settings['grafana_reviewer_password']).encode()).decode()
TOKEN = settings['webhook_url'].rsplit('/', 1)[1]
evidence = {'domain': BASE, 'release': settings['release_id'], 'checks': []}


def get(url, auth=False):
    headers = {'Authorization': 'Basic ' + AUTH} if auth else {}
    with urlopen(Request(url, headers=headers), timeout=15) as response:
        return json.load(response)


def wait_for(description, check, timeout=150):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        try:
            value = check()
            if value:
                print('PASS:', description, flush=True)
                evidence['checks'].append(description)
                return value
        except (URLError, IndexError, KeyError):
            pass
        time.sleep(5)
    raise AssertionError('Timed out: ' + description)


def query(expression):
    url = BASE + '/grafana/api/datasources/proxy/uid/prometheus/api/v1/query?'
    return get(url + urlencode({'query': expression}), True)['data']['result']


def incoming():
    return get('https://webhook.site/token/' + TOKEN + '/requests?sorting=newest')['data']


wait_for('public HTTPS and database readiness', lambda: get(BASE + '/health')['status'] == 'healthy')
assert get(BASE + '/version')['version'] == settings['release_id']
for uid in ['microblog-application', 'microblog-infrastructure']:
    dashboard = get(BASE + '/grafana/api/dashboards/uid/' + uid, True)
    assert len(dashboard['dashboard']['panels']) >= 4
    print('PASS: provisioned dashboard', uid, flush=True)
    evidence['checks'].append('dashboard ' + uid)
wait_for('application scrape is UP', lambda: query('up{job="microblog"}')[0]['value'][1] == '1')
wait_for('all four VM exporters are UP',
         lambda: query('sum(up{job="node_exporter"})')[0]['value'][1] == '4')
selector = 'microblog_errors_total{job="microblog",endpoint="main.trigger_error"}'
baseline = wait_for('initial error counter is visible in Grafana', lambda: query(selector))
before = float(baseline[0]['value'][1])
seen = {event['uuid'] for event in incoming()}
try:
    urlopen(BASE + '/debug/error', timeout=15)
except HTTPError as error:
    assert error.code == 500
else:
    raise AssertionError('Test endpoint did not generate HTTP 500')
print('PASS: intentional HTTP 500 generated', flush=True)
wait_for('new application error is visible in Grafana',
         lambda: float(query(selector)[0]['value'][1]) > before)
wait_for('MicroblogApplicationError is firing',
         lambda: query('ALERTS{alertname="MicroblogApplicationError",alertstate="firing"}'))


def find_notification():
    for event in incoming():
        if event['uuid'] in seen:
            continue
        content = json.loads(event.get('content', '{}'))
        if content.get('status') == 'firing' and any(
                alert['labels'].get('alertname') == 'MicroblogApplicationError'
                for alert in content.get('alerts', [])):
            return event
    return None


notification = wait_for('new firing notification delivered to webhook.site', find_notification)
evidence['webhook_request_id'] = notification['uuid']
evidence['webhook_received_at'] = notification['created_at']
(ROOT / '.deployment/live-verification.json').write_text(json.dumps(evidence, indent=2))
print('Live deployment checks passed; evidence saved locally.')
