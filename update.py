"""Refresh the stream links in every .m3u file in this repo from iptv-org.

Channels are matched by tvg-id. Each channel keeps its group (category);
its link is replaced with the latest one. Channels that iptv-org has
removed are dropped.
"""
import glob
import re
import urllib.request

SOURCE = "https://raw.githubusercontent.com/iptv-org/iptv/gh-pages/index.m3u"


def parse(text):
    lines = text.splitlines()
    entries, i = [], 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            block = [lines[i]]
            i += 1
            while i < len(lines) and not lines[i].startswith("#EXTINF"):
                if lines[i].strip():
                    block.append(lines[i])
                i += 1
            entries.append(block)
        else:
            i += 1
    return entries


def tvg_id(extinf):
    m = re.search(r'tvg-id="([^"]*)"', extinf)
    return m.group(1) if m else ""


def url(block):
    return next((l for l in block if l.startswith("http")), "")


def group(extinf):
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else ""


latest = {}
with urllib.request.urlopen(SOURCE, timeout=120) as r:
    for block in parse(r.read().decode("utf-8")):
        if "Geo-blocked" in block[0]:
            continue
        cid = tvg_id(block[0])
        if cid:
            latest.setdefault(cid, []).append(block)

for path in sorted(glob.glob("*.m3u")):
    old = parse(open(path, encoding="utf-8").read())
    out, kept, dropped = ["#EXTM3U"], 0, []
    for block in old:
        cid = tvg_id(block[0])
        options = latest.get(cid)
        if not options:
            dropped.append(block[0].rsplit(",", 1)[-1])
            continue
        same = [b for b in options if url(b) == url(block)]
        new = same[0] if same else options[0]
        extinf = re.sub(r'group-title="[^"]*"',
                        f'group-title="{group(block[0])}"', new[0])
        out += [extinf] + new[1:]
        kept += 1
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"{path}: {kept} channels kept, {len(dropped)} removed {dropped}")
