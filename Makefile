EXEC = docker exec hq-controller ansible-playbook
.PHONY: up bootstrap deploy test attack recover down
up:	; docker compose up -d --build
bootstrap:	; $(EXEC) playbooks/00_bootstrap.yml
# täielik juurutus õiges järjekorras; lõpus FIM baseline
deploy: bootstrap
	$(EXEC) playbooks/01_deploy_agents.yml
	$(EXEC) playbooks/02_generate_cmdb.yml
	$(EXEC) playbooks/03_profiles.yml
	$(EXEC) playbooks/04_hardening.yml
	$(EXEC) playbooks/06_fleet_backup.yml
	$(EXEC) playbooks/05_security_audit.yml -e init_baseline=true
test:	; ./scripts/test_week1.sh
attack:	; ./scripts/chaos_attack.sh
recover:	; $(EXEC) playbooks/07_incident_response.yml
down:	; docker compose down -v
