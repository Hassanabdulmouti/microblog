"""Provision the kmom04 Azure topology and write an Ansible inventory."""
import ipaddress
import json
import os
from pathlib import Path
import subprocess
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / '.deployment'
STATE.mkdir(mode=0o700, exist_ok=True)
GROUP = os.environ.get('AZURE_RESOURCE_GROUP', 'DIDA-HAAD23-DV1673-H25-LP2')
key = Path(os.environ.get('MICROBLOG_SSH_KEY', str(Path.home() / '.ssh/dbwebb')))
with urlopen('https://api.ipify.org', timeout=15) as response:
    public_ip = str(ipaddress.ip_address(response.read().decode().strip()))
parameters = {
    'sshCidr': {'value': public_ip + '/32'},
    'sshPublicKey': {'value': Path(str(key) + '.pub').read_text().strip()},
    'dnsLabel': {'value': os.environ.get('MICROBLOG_DNS_LABEL', 'haad23-microblog')},
}
parameter_file = STATE / 'azure-parameters.json'
parameter_file.write_text(json.dumps(parameters))
parameter_file.chmod(0o600)
base = ['az', 'deployment', 'group']
args = ['--resource-group', GROUP, '--name', 'kmom04-rebuild',
        '--template-file', str(ROOT / 'ansible/cloud/kmom04.json'),
        '--parameters', '@' + str(parameter_file), '-o', 'json']
print('Validating kmom04 Azure deployment...', flush=True)
subprocess.run(base + ['validate'] + args, check=True, stdout=subprocess.DEVNULL)
print('Creating/updating four kmom04 VMs and networking...', flush=True)
result = json.loads(subprocess.check_output(base + ['create'] + args))
(STATE / 'azure-result.json').write_text(json.dumps(result, indent=2))
outputs = result['properties']['outputs']
hosts = outputs['hosts']['value']
children = {}
for role, values in hosts.items():
    children[role] = {'hosts': {role: {
        'ansible_host': values['public_ip'],
        'monitoring_address': values['private_ip'],
        'private_ip': values['private_ip'],
    }}}
inventory = {'all': {'vars': {
    'ansible_user': 'azureuser',
    'ansible_ssh_private_key_file': str(key),
    'ansible_python_interpreter': '/usr/bin/python3',
    'ansible_ssh_common_args': '-o StrictHostKeyChecking=accept-new',
    'domain_name': outputs['domain']['value'],
    'app_upstream_host': hosts['appserver']['private_ip'],
}, 'children': {'devops': {'children': children}}}}
(ROOT / 'ansible/kmom04.inventory.yml').write_text(json.dumps(inventory, indent=2))
print('Domain:', outputs['domain']['value'], flush=True)
print('Inventory written to ansible/kmom04.inventory.yml', flush=True)
