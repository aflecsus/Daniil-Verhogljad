#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Koostab kollektori JSON-idest CMDB & Turvaseire armatuurlaua (/var/www/html/index.html).
Kasutus: render_dashboard.py [--init-baseline]"""
import glob, html, json, os, sys, time

DATA, BASE = os.environ.get("CF_DATA","/opt/cyberfleet/data"), os.environ.get("CF_BASE","/opt/cyberfleet/baseline")
OUT = os.environ.get("CMDB_OUT", "/var/www/html/index.html")
HERE = os.path.dirname(os.path.abspath(__file__))
POLICY = json.load(open(os.path.join(HERE, "..", "policy.json")))
SEV = {"CRIT": 3, "WARN": 2, "INFO": 1, "OK": 0}


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def hosts():
    names = set()
    for f in glob.glob(DATA + "/*.json"):
        names.add(os.path.basename(f).split(".")[0])
    return sorted(names)


def allowed_ports(host):
    ap = POLICY["allowed_ports"]
    return set(ap.get("default", [22])) | set(ap.get(host, []))


def evaluate(host, inv, sec, base):
    alerts, now = [], time.time()
    for label, d in (("inventory", inv), ("security", sec)):
        if d and now - d.get("ts", 0) > POLICY.get("stale_after_seconds", 900):
            alerts.append(("WARN", "%s andmed aegunud (%s)" % (label, d.get("collected", "?"))))
    if not sec:
        return alerts
    s = sec["security"]
    for u in s["uid0"]:
        if u != "root":
            alerts.append(("CRIT", "Volitamata UID=0 (root) konto: %s" % u))
    for p in s["deleted_procs"]:
        alerts.append(("CRIT", "Protsess kustutatud binaariga: %s (pid %s, %s)" % (p["name"], p["pid"], p["path"])))
    ok_ports = allowed_ports(host)
    for p in s["ports"]:
        if p["port"] not in ok_ports:
            alerts.append(("CRIT", "Volitamata avatud port %d (%s)" % (p["port"], p["proc"])))
    if base:
        for path, h in s["hashes"].items():
            if path in base.get("hashes", {}) and base["hashes"][path] != h:
                alerts.append(("CRIT", "FIM: %s räsi muutus" % path))
    else:
        alerts.append(("INFO", "FIM baseline puudub (käivita 05 koos -e init_baseline=true)"))
    if s.get("ssh_password_auth") == "yes":
        alerts.append(("WARN", "SSH PasswordAuthentication = yes (drift!)"))
    if s.get("fin_files") == 0:
        alerts.append(("CRIT", "Finantsdokumentide kaust on TÜHI (võimalik lunavara)"))
    return alerts


def main():
    init = "--init-baseline" in sys.argv
    os.makedirs(BASE, exist_ok=True)
    rows, all_alerts, counts = [], [], {"CRIT": 0, "WARN": 0, "INFO": 0}
    for h in hosts():
        inv, sec = load("%s/%s.inventory.json" % (DATA, h)), load("%s/%s.security.json" % (DATA, h))
        if init and sec:
            json.dump({"hashes": sec["security"]["hashes"], "fin_files": sec["security"]["fin_files"],
                       "created": time.strftime("%F %T")}, open("%s/%s.json" % (BASE, h), "w"))
        base = load("%s/%s.json" % (BASE, h))
        alerts = evaluate(h, inv, sec, base)
        for sev, msg in alerts:
            if sev in counts:
                counts[sev] += 1
            if sev != "OK":
                all_alerts.append((h, sev, msg))
        worst = max([SEV[a[0]] for a in alerts] + [0])
        rows.append((h, inv, sec, worst))

    e = html.escape
    css = """body{font-family:system-ui,sans-serif;background:#10141a;color:#dde3ea;margin:20px}
    h1{margin:0}table{border-collapse:collapse;width:100%;margin:12px 0 24px}
    th,td{border:1px solid #2b3440;padding:6px 8px;text-align:left;font-size:13px;vertical-align:top}
    th{background:#1b222c}.crit{background:#6b1515;color:#fff;font-weight:600}.warn{background:#6b5a15}
    .info{background:#1d3550}.ok{background:#12301c}.badge{padding:3px 10px;border-radius:10px;font-weight:700}
    .b-crit{background:#d32f2f}.b-ok{background:#2e7d32}.b-warn{background:#f9a825;color:#000}small{color:#8b98a8}"""
    status = ("<span class='badge b-crit'>%d KRIITILIST HÄIRET</span>" % counts["CRIT"]) if counts["CRIT"] else \
             ("<span class='badge b-warn'>%d hoiatust</span>" % counts["WARN"] if counts["WARN"] else
              "<span class='badge b-ok'>KÕIK ROHELINE</span>")
    p = ["<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='refresh' content='30'>",
         "<title>CyberFleet CMDB</title><style>%s</style></head><body>" % css,
         "<h1>CyberFleet 2026 - CMDB &amp; Turvaseire %s</h1>" % status,
         "<small>Uuendatud %s (automaatne värskendus 30 s)</small>" % time.strftime("%Y-%m-%d %H:%M:%S"),
         "<h2>Turvahäired</h2>"]
    if all_alerts:
        p.append("<table><tr><th>Sõlm</th><th>Tase</th><th>Häire</th></tr>")
        for h, sev, msg in sorted(all_alerts, key=lambda a: -SEV[a[1]]):
            p.append("<tr class='%s'><td>%s</td><td>%s</td><td>%s</td></tr>" % (sev.lower(), e(h), sev, e(msg)))
        p.append("</table>")
    else:
        p.append("<p class='ok' style='padding:8px'>Häireid ei ole.</p>")
    p.append("<h2>CMDB - seadmepark</h2><table><tr><th>Sõlm</th><th>IP / tsoon</th><th>OS / tuum</th>"
             "<th>RAM</th><th>Pakette</th><th>Sisselogimisõigusega kasutajad</th><th>Avatud pordid</th><th>Mootor</th></tr>")
    for h, inv, sec, worst in rows:
        cls = {3: "crit", 2: "warn", 1: "info", 0: "ok"}[worst]
        if not inv:
            p.append("<tr class='%s'><td>%s</td><td colspan='7'>inventari andmed puuduvad</td></tr>" % (cls, e(h)))
            continue
        i = inv["inventory"]
        users = ", ".join("%s(%s)" % (u["username"], u["uid"]) for u in i["login_users"])
        ports = ", ".join("%d/%s" % (x["port"], x["proc"]) for x in i["ports"]) or "-"
        p.append("<tr class='%s'><td><b>%s</b></td><td>%s<br><small>%s</small></td><td>%s<br><small>%s</small></td>"
                 "<td>%d MB</td><td>%d <small>(%s)</small></td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                     cls, e(h), e(", ".join(i["ips"])), e(i["zone"]), e(i["os"]), e(i["kernel"]), i["ram_mb"],
                     i["pkg_count"], e(i["pkg_source"]), e(users), e(ports), e(inv["engine"])))
    p.append("</table></body></html>")
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(p))
    os.replace(tmp, OUT)
    print("dashboard: %s | CRIT=%d WARN=%d" % (OUT, counts["CRIT"], counts["WARN"]))


if __name__ == "__main__":
    main()
