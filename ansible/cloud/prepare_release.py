"""Package local application code and prepare private deployment settings."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import tarfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / '.deployment'
STATE.mkdir(mode=0o700, exist_ok=True)
archive = STATE / 'microblog.tar.gz'
with tarfile.open(archive, 'w:gz') as output:
    for name in ['app', 'migrations', 'requirements', 'requirements.txt', 'microblog.py', 'boot.sh']:
        output.add(ROOT / name, arcname=name,
                   filter=lambda item: None if '__pycache__' in item.name or item.name.endswith('.pyc') else item)
release_id = hashlib.sha256(archive.read_bytes()).hexdigest()[:16]
result = json.loads((STATE / 'azure-result.json').read_text())['properties']['outputs']
private_file = ROOT / 'ansible/kmom04.private.yml'
private = json.loads(private_file.read_text()) if private_file.exists() else {}
private.setdefault('microblog_secret_key', secrets.token_hex(32))
private.setdefault('microblog_db_password', secrets.token_hex(24))
private.setdefault('grafana_admin_password', secrets.token_urlsafe(24))
private.setdefault('grafana_reviewer_password', secrets.token_urlsafe(18))
private['grafana_admin_user'] = 'admin'
if not private.get('webhook_url'):
    body = json.dumps({'default_status': 200, 'default_content': 'OK', 'expiry': 604800}).encode()
    with urlopen(Request('https://webhook.site/token', body, {'Content-Type': 'application/json'}), timeout=30) as response:
        token = json.load(response)
    private['webhook_url'] = 'https://webhook.site/' + token['uuid']
    private['webhook_expires_at'] = token.get('expires_at')
private.update({
    'domain_name': result['domain']['value'],
    'app_upstream_host': result['hosts']['value']['appserver']['private_ip'],
    'app_archive': str(archive),
    'release_id': release_id,
    'ansible_user': 'azureuser',
    'ansible_ssh_private_key_file': os.environ.get('MICROBLOG_SSH_KEY', str(Path.home() / '.ssh/dbwebb')),
    'microblog_database_url': 'mysql+pymysql://microblog:' + private['microblog_db_password'] +
                             '@' + result['hosts']['value']['database']['private_ip'] + '/microblog',
})
private_file.write_text(json.dumps(private, indent=2))
private_file.chmod(0o600)
print('Packaged local kmom04 snapshot:', release_id)
print('Private settings saved to ansible/kmom04.private.yml (not printed).')
