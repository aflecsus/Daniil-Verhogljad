#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CyberFleet kollektor - jookseb igal sõlmel ja prindib JSON-i.

Režiimid:
  inventory  - CMDB andmed (OS, tuum, RAM, pakettide arv, kasutajad, pordid)
  security   - HIDS/FIM andmed (räsid, kustutatud binaaridega protsessid, UID=0, pordid)
  remediate  - tapab pahavaralised protsessid/volitamata kuulajad, eemaldab võõrad UID=0 kontod
Kasutab Osquery SQL-i, kui osqueryi on olemas; Alpine'is (ilma osqueryta) /proc põhist varuvarianti.
"""
import glob, hashlib, json, os, platform, re, shutil, signal, socket, subprocess, sys, time

os.environ["PATH"] = os.environ.get("PATH", "") + ":/usr/sbin:/sbin:/usr/local/sbin"
POLICY_FILE = "/etc/cyberfleet/policy.json"
DEFAULT_POLICY = {
    "allowed_ports": {"default": [22]},
    "critical_files": ["/etc/passwd", "/etc/shadow", "/etc/ssh/sshd_config", "/etc/sudoers"],
    "fin_dir": "/home/raamatupidaja/Raamatupidamine_2026",
}
ZONES = {"172.30.10.": "mgmt_net", "172.30.20.": "corp_net", "172.30.30.": "dmz_iot"}
OSQ = shutil.which("osqueryi")


def load_policy():
    try:
        with open(POLICY_FILE) as f:
            p = json.load(f)
    except Exception:
        p = {}
    for k, v in DEFAULT_POLICY.items():
        p.setdefault(k, v)
    return p


def osq(sql):
    """Osquery SQL -> list of dict; None kui osquery puudub või päring ebaõnnestub."""
    if not OSQ:
        return None
    try:
        r = subprocess.run([OSQ, "--json", sql], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout or "[]")
    except Exception:
        return None


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


def read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


# ---------------- inventory ----------------
def os_pretty():
    for line in read("/etc/os-release").splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip('"')
    return platform.system()


def ip_list():
    out = sh("ip -4 -o addr show")
    return [m for m in re.findall(r"inet (\d+\.\d+\.\d+\.\d+)/", out) if not m.startswith("127.")]


def zones(ips):
    return sorted({z for ip in ips for pre, z in ZONES.items() if ip.startswith(pre)})


def ram_mb():
    r = osq("SELECT physical_memory FROM system_info;")
    if r:
        return int(r[0]["physical_memory"]) // 1048576
    for line in read("/proc/meminfo").splitlines():
        if line.startswith("MemTotal"):
            return int(line.split()[1]) // 1024
    return 0


def pkg_count():
    for table in ("deb_packages", "rpm_packages"):
        r = osq("SELECT COUNT(*) AS c FROM %s;" % table)
        if r and int(r[0]["c"]) > 0:
            return int(r[0]["c"]), table
    for cmd, name in (("dpkg-query -W -f='x\\n' 2>/dev/null | wc -l", "dpkg"),
                      ("rpm -qa 2>/dev/null | wc -l", "rpm"),
                      ("apk info 2>/dev/null | wc -l", "apk")):
        n = sh(cmd)
        if n.isdigit() and int(n) > 0:
            return int(n), name
    return 0, "unknown"


def passwd_entries():
    out = []
    for line in read("/etc/passwd").splitlines():
        p = line.split(":")
        if len(p) >= 7:
            try:
                out.append({"username": p[0], "uid": int(p[2]), "shell": p[6]})
            except ValueError:
                pass
    return out


def login_users():
    r = osq("SELECT username, uid, shell FROM users WHERE shell NOT LIKE '%nologin' "
            "AND shell NOT LIKE '%false' AND shell != '';")
    if r is not None:
        return [{"username": x["username"], "uid": int(x["uid"]), "shell": x["shell"]} for x in r]
    return [u for u in passwd_entries() if not u["shell"].endswith(("nologin", "false")) and u["shell"]]


# ---------------- ports ----------------
def is_loop(addr):
    return (len(addr) == 8 and addr.endswith("7F")) or addr == "00000000000000000000000001000000"


def listeners_proc():
    """{port: set(pid)} mitte-loopback TCP kuulajatele, otse /proc kaudu."""
    inode_port = {}
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        for line in read(f).splitlines()[1:]:
            p = line.split()
            if len(p) < 10 or p[3] != "0A":
                continue
            addr, port = p[1].rsplit(":", 1)
            if not is_loop(addr):
                inode_port[p[9]] = int(port, 16)
    res = {port: set() for port in inode_port.values()}
    for fd in glob.glob("/proc/[0-9]*/fd/*"):
        try:
            tgt = os.readlink(fd)
        except OSError:
            continue
        if tgt.startswith("socket:[") and tgt[8:-1] in inode_port:
            res[inode_port[tgt[8:-1]]].add(int(fd.split("/")[2]))
    return res


def comm(pid):
    return read("/proc/%d/comm" % pid).strip() or "?"


def listening_ports():
    found = {}
    r = osq("SELECT DISTINCT lp.port AS port, COALESCE(p.name,'?') AS proc, lp.address AS address "
            "FROM listening_ports lp LEFT JOIN processes p ON lp.pid = p.pid "
            "WHERE lp.port != 0 AND lp.protocol = 6;")
    for x in r or []:
        if x["address"].startswith("127.") or x["address"] == "::1":
            continue
        found[int(x["port"])] = x["proc"]
    if not found:
        for port, pids in listeners_proc().items():
            found[port] = comm(sorted(pids)[0]) if pids else "?"
    return [{"port": p, "proc": n} for p, n in sorted(found.items())]


# ---------------- security ----------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def file_hashes(paths):
    quoted = ",".join("'%s'" % p for p in paths)
    r = osq("SELECT path, sha256 FROM hash WHERE path IN (%s);" % quoted)
    res = {x["path"]: x["sha256"] for x in (r or []) if x.get("sha256")}
    for p in paths:
        if p not in res and os.path.isfile(p):
            try:
                res[p] = sha256_file(p)
            except OSError:
                pass
    return res


def deleted_procs():
    found = {}
    for x in osq("SELECT pid, name, path FROM processes WHERE on_disk = 0;") or []:
        found[int(x["pid"])] = {"pid": int(x["pid"]), "name": x["name"], "path": x["path"]}
    for d in glob.glob("/proc/[0-9]*"):
        try:
            exe = os.readlink(d + "/exe")
        except OSError:
            continue
        if exe.endswith(" (deleted)"):
            pid = int(d.split("/")[-1])
            found.setdefault(pid, {"pid": pid, "name": comm(pid), "path": exe[:-10]})
    return sorted(found.values(), key=lambda x: x["pid"])


def uid0_users():
    r = osq("SELECT username FROM users WHERE uid = 0;")
    names = [x["username"] for x in r] if r else []
    names += [u["username"] for u in passwd_entries() if u["uid"] == 0]
    return sorted(set(names))


def ssh_password_auth():
    out = sh("sshd -T 2>/dev/null | grep -i '^passwordauthentication'")
    return out.split()[-1] if out else "?"


def fin_files(path):
    if not os.path.isdir(path):
        return None
    return sum(len(files) for _, _, files in os.walk(path))


# ---------------- remediation ----------------
def kill(pid):
    if pid in (1, os.getpid()):
        return False
    try:
        os.kill(pid, signal.SIGKILL)
        return True
    except OSError:
        return False


def drop_foreign_uid0():
    removed, keep = [], []
    lines = read("/etc/passwd").splitlines(True)
    for line in lines:
        p = line.split(":")
        if len(p) >= 3 and p[2] == "0" and p[0] != "root":
            removed.append(p[0])
        else:
            keep.append(line)
    if removed:
        with open("/etc/passwd", "w") as f:
            f.writelines(keep)
        shadow = [l for l in read("/etc/shadow").splitlines(True) if l.split(":")[0] not in removed]
        with open("/etc/shadow", "w") as f:
            f.writelines(shadow)
    return removed


def remediate(policy, host):
    actions = []
    ports = policy["allowed_ports"]
    allowed = set(ports.get(host, ports.get("default", [22]))) | (
        set(ports["default"]) if host in ports else set())
    for port, pids in listeners_proc().items():
        if port not in allowed:
            for pid in pids:
                name = comm(pid)
                if kill(pid):
                    actions.append("tapetud protsess %s (pid %d), volitamata port %d" % (name, pid, port))
    for p in deleted_procs():
        if re.match(r"^(/tmp|/var/tmp|/dev/shm)/", p["path"] or ""):
            if kill(p["pid"]):
                actions.append("tapetud kustutatud binaariga protsess %s (pid %d, %s)" % (p["name"], p["pid"], p["path"]))
    for u in drop_foreign_uid0():
        actions.append("eemaldatud volitamata UID=0 konto %s" % u)
    return actions


# ---------------- main ----------------
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    policy, host = load_policy(), socket.gethostname()
    if mode == "remediate":
        print(json.dumps({"host": host, "actions": remediate(policy, host)}))
        return
    out = {"host": host, "ts": int(time.time()), "collected": time.strftime("%Y-%m-%d %H:%M:%S"),
           "engine": "osquery" if OSQ else "procfs"}
    ports = listening_ports()
    if mode in ("inventory", "all"):
        ips = ip_list()
        n, mgr = pkg_count()
        out["inventory"] = {
            "hostname": host, "ips": ips, "zone": ", ".join(zones(ips)) or "?",
            "os": os_pretty(), "kernel": platform.release(), "ram_mb": ram_mb(),
            "pkg_count": n, "pkg_source": mgr, "login_users": login_users(), "ports": ports,
        }
    if mode in ("security", "all"):
        out["security"] = {
            "hashes": file_hashes(policy["critical_files"]), "deleted_procs": deleted_procs(),
            "uid0": uid0_users(), "ports": ports, "ssh_password_auth": ssh_password_auth(),
            "fin_files": fin_files(policy["fin_dir"]),
        }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
