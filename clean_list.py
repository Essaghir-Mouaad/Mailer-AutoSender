#!/usr/bin/env python3
"""Clean emails_1.csv BEFORE sending.

Steps: normalise -> reject bad syntax -> fix common domain typos -> remove
duplicates -> check each domain can receive mail (MX/A lookup) -> sort so the
best addresses go first.

Needs:  pip install dnspython
Run:    python3 clean_list.py
Output: emails_clean.csv (to send)   emails_rejected.csv (with the reason)
"""
import csv
import re
import sys
from pathlib import Path

try:
    import dns.exception
    import dns.resolver
except ImportError:
    sys.exit("Install the DNS library first:  pip install dnspython")

BASE = Path(__file__).parent
SRC = BASE / "emails_1.csv"

RX = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)*\.[a-z]{2,}$")
TYPOS = {"gmial.com": "gmail.com", "gmal.com": "gmail.com", "gmail.con": "gmail.com",
         "hotmial.com": "hotmail.com", "hotmail.con": "hotmail.com",
         "yahoo.con": "yahoo.com", "yaho.fr": "yahoo.fr", "outlok.com": "outlook.com"}
FREE = {"gmail.com", "yahoo.fr", "yahoo.com", "hotmail.com", "hotmail.fr",
        "outlook.com", "outlook.fr", "live.fr", "live.com"}
# old ISP domains: many abandoned mailboxes -> send last
LEGACY = {"menara.ma", "wanadoo.net.ma", "wanadoopro.ma", "iam.net.ma",
          "casanet.net.ma", "marocnet.net.ma", "ecs.net.ma"}

resolver = dns.resolver.Resolver()
resolver.lifetime = 6
_cache = {}


def domain_status(domain):
    """'ok' | 'dead' | 'unknown' (network problem, keep the address)."""
    if domain in _cache:
        return _cache[domain]
    status = "unknown"
    try:
        resolver.resolve(domain, "MX")
        status = "ok"
    except dns.resolver.NoAnswer:  # no MX: mail servers fall back to A record
        try:
            resolver.resolve(domain, "A")
            status = "ok"
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            status = "dead"
        except dns.exception.DNSException:
            status = "unknown"
    except dns.resolver.NXDOMAIN:
        status = "dead"
    except dns.exception.DNSException:
        status = "unknown"
    _cache[domain] = status
    return status


def normalise(raw):
    e = raw.strip().lower().replace("mailto:", "").strip(" \t\r\n.,;:<>\"'")
    return e.replace(" ", "")


def main():
    with open(SRC, newline="", encoding="utf-8") as f:
        raw = [r.get("Email", "") for r in csv.DictReader(f)]

    keep, rejected, seen = [], [], set()
    for r in raw:
        if not r.strip():
            continue
        e = normalise(r)
        if "@" in e:
            local, dom = e.rsplit("@", 1)
            dom = TYPOS.get(dom, dom)
            e = f"{local}@{dom}"
        if not RX.match(e):
            rejected.append((r.strip(), "invalid syntax"))
        elif e in seen:
            rejected.append((e, "duplicate"))
        else:
            seen.add(e)
            keep.append(e)

    domains = sorted({e.split("@")[1] for e in keep})
    print(f"Checking {len(domains)} domains (takes a few minutes)...")
    for i, d in enumerate(domains, 1):
        domain_status(d)
        if i % 50 == 0:
            print(f"  {i}/{len(domains)}")

    unknown = sum(1 for d in domains if _cache[d] == "unknown")
    if unknown > len(domains) * 0.3:
        sys.exit(f"{unknown} lookups failed: check your internet connection and rerun.")

    good = []
    for e in keep:
        d = e.split("@")[1]
        if _cache[d] == "dead":
            rejected.append((e, "domain does not exist / cannot receive mail"))
        else:
            good.append(e)

    def priority(e):
        d = e.split("@")[1]
        return 2 if d in LEGACY else 1 if d in FREE else 0

    good.sort(key=priority)  # company domains, then free webmail, then legacy ISPs

    with open(BASE / "emails_clean.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Email"])
        w.writerows([[e] for e in good])
    with open(BASE / "emails_rejected.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Email", "Reason"])
        w.writerows(rejected)

    print(f"\nInput: {len(raw)} | Clean: {len(good)} | Rejected: {len(rejected)}")
    print(f"Days needed at 50/day: {-(-len(good) // 50)}")


if __name__ == "__main__":
    main()
