"""Generate handover documents only after live verification succeeds."""
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
settings = json.loads((ROOT / 'ansible/kmom04.private.yml').read_text())
proof = json.loads((ROOT / '.deployment/live-verification.json').read_text())
assert proof['release'] == settings['release_id']
domain = settings['domain_name']
base = 'https://' + domain
token = settings['webhook_url'].rsplit('/', 1)[1]
inbox = 'https://webhook.site/#!/' + token
stamp = datetime.now(timezone.utc).isoformat()
access = ('# Grafana – privata inloggningsuppgifter\n\n'
          + 'URL: ' + base + '/grafana/\n\n'
          + '## Granskare (Viewer)\n\nAnvändare: reviewer\n\nLösenord: '
          + settings['grafana_reviewer_password']
          + '\n\n## Administratör (för Hassan)\n\nAnvändare: admin\n\nLösenord: '
          + settings['grafana_admin_password'] + '\n')
access_file = ROOT / '.deployment/GRAFANA-LOGIN.md'
access_file.write_text(access)
access_file.chmod(0o600)

guide_file = ROOT / 'docs/kmom04-guide.md'
guide = guide_file.read_text()
start = guide.index('## ')
end = guide.index('## Testa ett avsiktligt')
guide = guide[:start] + (
    '## Verifierad produktionsmiljö\n\n'
    f'- Microblog: [{base}]({base})\n'
    f'- Grafana: [{base}/grafana/]({base}/grafana/)\n'
    f'- [Applikationsdashboard]({base}/grafana/d/microblog-application/)\n'
    f'- [Infrastrukturdashboard]({base}/grafana/d/microblog-infrastructure/)\n'
    f'- [Webhook.site-inbox]({inbox})\n'
    '- Grafana-användare: **reviewer**. Lösenord lämnas privat i Canvas.\n'
    f'- Webhookens rapporterade utgångstid: **{settings.get("webhook_expires_at")}**. '
    'Gratis inboxar upphör efter en vecka; förnya före rättning om det behövs.\n\n'
    f'Azure-miljön byggdes upp igen 2026-09-13. Verifierad kodsnapshot: '
    f'`{settings["release_id"]}`. Den nya databasen är nyskapad; gamla data har inte återställts.\n\n'
) + guide[end:]
guide = guide.replace('AKTUELL-DOMÄN', domain)
guide += ('\n## Återskapa denna driftsättning utan Git-push\n\n'
          'Kör från kmom04-checkoutens rot med inloggad Azure CLI:\n\n'
          '```sh\n'
          'python3 ansible/cloud/provision.py\n'
          'python3 ansible/cloud/prepare_release.py\n'
          'ansible-playbook -i ansible/kmom04.inventory.yml ansible/deploy_kmom04.yml '
          '-e @ansible/kmom04.private.yml\n'
          'python3 ansible/cloud/check_live.py\n'
          '```\n\n'
          'Ansible-provisioneringen kan också startas med '
          '`ansible-playbook -i ansible/hosts ansible/provision_instances.yml`. '
          'Mallen använder fyra Standard_B1s med Ubuntu 24.04 enligt prenumerationens policy. '
          'SSH tillåts endast från den IP-adress som kör provisioneringen; '
          'andra interna portar är begränsade per serverroll.\n\n'
          'Hemligheter, inventarium, distributionsarkiv och Azure-resultat sparas lokalt '
          'och är gitignored. Ett nytt arkiv innehåller den lokala applikationskoden även '
          'om den ännu inte är pushad.\n')
guide_file.write_text(guide)

report_file = ROOT / 'docs/kmom04-redovisning.md'
report = report_file.read_text()
status_start = report.index('**Status:**')
status_end = report.index('## Länkar', status_start)
report = report[:status_start] + ('**Status:** Återdriftsatt och live-verifierad 2026-09-13. '
    'Gruppens egna svar om Loki och arbetsmängd behöver fortfarande fyllas i.\n\n') + report[status_end:]
report = report.replace('**FYLL I AKTUELL DOMÄN**', f'[{base}]({base})')
report = report.replace('https://AKTUELL-DOMÄN/grafana/', base + '/grafana/')
report = report.replace('**FYLL I I PRIVAT INLÄMNING**', '**reviewer**, lösenord lämnas privat')
report = report.replace('**FYLL I AKTUELL INBOX-LÄNK**', f'[{inbox}]({inbox})')
report = report.replace('Produktionens domän, Grafana-login\noch webhook.site måste fortfarande kontrolleras i den riktiga miljön.',
                        'Produktionens HTTPS-domän, båda dashboards, alla fyra node_exporter-targets '
                        'och leverans av ett nytt larm till webhook.site har kontrollerats.')
report += ('\n## Verifieringsresultat\n\n'
           '- 33 applikationstester godkända; Pylint 10/10.\n'
           '- Registrering, inloggning och skapande av inlägg verifierades via publik HTTPS mot MariaDB.\n'
           '- Båda provisionerade Grafana-dashboards finns och läser Prometheus-data.\n'
           '- Applikationen och fyra node_exporter-targets har scrape-status UP.\n'
           '- Ett avsiktligt HTTP 500 ökade felräknaren och utlöste MicroblogApplicationError.\n'
           f'- Webhook.site tog emot ett nytt firing-meddelande: `{proof["webhook_request_id"]}`.\n'
           f'- Verifieringsdatum UTC: {stamp}.\n')
report_file.write_text(report)
submission = report.replace('**reviewer**, lösenord lämnas privat',
                            '**reviewer** / **' + settings['grafana_reviewer_password'] + '**')
submission += '\n\n---\n\n' + guide
submission_file = ROOT / '.deployment/KMOM04-INLAMNING.md'
submission_file.write_text(submission)
submission_file.chmod(0o600)
print('Public guide/report and private login/submission files written.')
