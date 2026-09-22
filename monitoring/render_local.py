"""Render the production Ansible templates for the isolated local demo."""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'monitoring/generated'
OUTPUT.mkdir(exist_ok=True)
env = Environment(loader=FileSystemLoader(ROOT / 'ansible/roles/monitoring/templates'),
                  undefined=StrictUndefined, keep_trailing_newline=True)
variables = dict(groups={'devops': ['node-exporter'], 'appserver': ['app']},
                 hostvars={'node-exporter': {}, 'app': {}},
                 microblog_metrics_port=5000,
                 prometheus_self_target='prometheus:9090',
                 prometheus_alertmanager_target='alertmanager:9093',
                 webhook_url='http://webhook:8080')
for name in ['prometheus.yml', 'alert_rules.yml', 'alertmanager.yml', 'grafana-dashboards.yml']:
    (OUTPUT / name).write_text(env.get_template(name + '.j2').render(**variables))
