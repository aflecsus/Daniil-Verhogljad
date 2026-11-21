#!/bin/bash
# hq-controller: SSH võtmepaar (Ed25519), kataloogid, Nginx ja cron
set -e
mkdir -p /root/.ssh /opt/cyberfleet/{data,baseline,staging,secret,vault} /var/www/html
chmod 700 /root/.ssh /opt/cyberfleet/secret
if [ ! -f /root/.ssh/id_ed25519 ]; then
  ssh-keygen -t ed25519 -N "" -C "ansible@hq-controller" -f /root/.ssh/id_ed25519
fi
if [ ! -f /var/www/html/index.html ]; then
  echo '<h1>CyberFleet CMDB</h1><p>Käivita: ansible-playbook playbooks/02_generate_cmdb.yml</p>' > /var/www/html/index.html
fi
touch /var/log/cyberfleet-drift.log /var/log/cyberfleet-audit.log
nginx
exec cron -f
