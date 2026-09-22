#!/usr/bin/env python3
"""Analyze Sims4Multiplayer diagnostic bundles and live logs.

Reads the newest (or given) host/join diagnostic folders and prints a short
verdict of what went wrong in a session. Stdlib only.

Examples::

    python tools/analyze_session.py
    python tools/analyze_session.py --received C:\\Users\\...\\received\\diag-...
    python tools/analyze_session.py --host-diag C:\\Users\\...\\diagnostics\\Sims4...
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter


DEFAULT_RECEIVED = os.path.join(
    os.environ.get("TEMP", os.environ.get("TMP", ".")),
    "simmp-launcher",
    "received",
)
DEFAULT_DIAG = os.path.join(
    os.environ.get("TEMP", os.environ.get("TMP", ".")),
    "simmp-launcher",
    "diagnostics",
)
DEFAULT_CLIENT_LOG = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Sims4Multiplayer",
    "client.log",
)


def _newest_dir(root, prefix=""):
    if not os.path.isdir(root):
        return None
    candidates = []
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if prefix and not name.startswith(prefix):
            continue
        candidates.append((os.path.getmtime(path), path))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _read_text(path, max_bytes=8_000_000):
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, "rb") as handle:
            raw = handle.read(max_bytes)
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _count(pattern, text, flags=0):
    return len(re.findall(pattern, text, flags))


def _sample(pattern, text, limit=5):
    return re.findall(pattern, text)[:limit]


def analyze_client_log(text, label):
    findings = []
    if not text.strip():
        findings.append(("warn", "%s: missing / empty game-client.log" % label))
        return findings

    connects = _count(r"\[MP\]\[NET\] Connected to ", text)
    disconnects = _count(r"\[MP\]\[NET\] Disconnected", text)
    player_ids = _sample(r"\[MP\]\[NET\] Player ID: (\d+)", text)
    holds = _count(r"Holding paused until", text)
    unpause = _sample(
        r"Applied room speed ([1-3]) -> \1",
        text,
    )
    gate_open = _count(r"TIME_SYNC speed=\d+ .*gate=open", text)
    gate_closed = _count(r"TIME_SYNC speed=\d+ .*gate=closed", text)
    locked = _count(r"OBJECT_LOCKED", text)
    alarm_spam = _count(r"sync alarm started", text)
    reconnects = _count(r"Auto-reconnect attempt", text)
    time_ready = _count(r"TIME_READY zone=", text)
    errors = _count(r"\[MP\]\[ERROR\]", text)

    findings.append(
        (
            "info",
            "%s: connects=%s disconnects=%s reconnects=%s TIME_READY=%s"
            % (label, connects, disconnects, reconnects, time_ready),
        )
    )
    if player_ids:
        findings.append(("info", "%s: player_ids seen=%s" % (label, ", ".join(player_ids[:8]))))
    if holds:
        findings.append(("ok", "%s: min_players hold fired %s time(s)" % (label, holds)))
    if unpause and holds:
        # Unpause while co-op hold is the classic desync signature.
        findings.append(
            (
                "fail",
                "%s: unpaused (speed>=1) while co-op hold also logged - "
                "TIME_SYNC ignored min_players (desync)" % label,
            )
        )
    if gate_open and not holds and connects:
        findings.append(
            (
                "warn",
                "%s: gate opened %s time(s), closed %s - check peer readiness"
                % (label, gate_open, gate_closed),
            )
        )
    if locked > 50:
        findings.append(
            (
                "fail",
                "%s: OBJECT_LOCKED spam (%s) - first client claimed the lot; "
                "peer cannot drive furniture/sims" % (label, locked),
            )
        )
    elif locked:
        findings.append(("warn", "%s: OBJECT_LOCKED=%s" % (label, locked)))
    sim_locks = _count(r"OBJECT_LOCKED: object 'sim:", text)
    if sim_locks >= 5:
        findings.append(
            (
                "warn",
                "%s: %s sim OBJECT_LOCKED (legacy exclusive claim) - rebuild "
                "with last-select-wins sim transfer if this build is old"
                % (label, sim_locks),
            )
        )
    mirror_lines = _count(r"\[MP\]\[MIRROR\]", text)
    sleep_starts = _count(r"Interaction start: sleep_", text)
    if sleep_starts and not mirror_lines:
        findings.append(
            (
                "fail",
                "%s: saw sleep Interaction start(s) but zero [MP][MIRROR] "
                "lines - peer never applied (logger/affordance)" % label,
            )
        )
    elif mirror_lines:
        findings.append(("ok", "%s: [MP][MIRROR]=%s" % (label, mirror_lines)))
    ownership_host = _count(r"Ownership ack for 'sim:[^']+': owner=\d+", text)
    if "world sync health" in text and "denied" in text:
        findings.append(
            (
                "warn",
                "%s: world sync health reported denied claims - peer owns the "
                "world this client wanted" % label,
            )
        )
    if alarm_spam > 100:
        findings.append(
            (
                "warn",
                "%s: sync alarm started logged %s times (log flood)" % (label, alarm_spam),
            )
        )
    if reconnects >= 4:
        findings.append(
            (
                "fail",
                "%s: auto-reconnect spun %s times - server port/config likely wrong "
                "or lobby died" % (label, reconnects),
            )
        )
    if errors and locked < errors:
        findings.append(("warn", "%s: %s ERROR lines (incl. non-lock)" % (label, errors)))
    if connects == 0:
        findings.append(("fail", "%s: never Connected - auto-connect did not land" % label))
    return findings


def analyze_server_log(text):
    findings = []
    if not text.strip():
        findings.append(("warn", "server-log.txt missing / empty"))
        return findings

    accepted = _sample(r"Player (\d+) \(([^)]+)\) accepted from", text)
    resumed = _count(r"resumed", text)
    disconnected = _count(r"\) disconnected", text)
    evicted = _count(r"Evicted ghost player", text)
    names = Counter(name for _, name in accepted)

    findings.append(
        (
            "info",
            "server: accepted=%s resumed=%s disconnects=%s ghost_evictions=%s"
            % (len(accepted), resumed, disconnected, evicted),
        )
    )
    if names:
        findings.append(
            ("info", "server names: " + ", ".join("%s×%s" % (n, c) for n, c in names.most_common()))
        )
    if "Sims4Player" in names:
        findings.append(
            (
                "fail",
                "server saw default name 'Sims4Player' - game loaded without "
                "launcher config (or stale Mods/Sims4Multiplayer.json)",
            )
        )
    if resumed == 0 and len(accepted) > 4:
        findings.append(
            (
                "warn",
                "no HELLO resumes - client_id not persisting or ghosts evicted "
                "before the game reconnected (60s TTL during long loads)",
            )
        )
    if evicted and len(accepted) > 2:
        findings.append(
            (
                "warn",
                "ghosts were evicted mid-session - lobby Start disconnect + slow "
                "game boot can burn the 60s ownership window",
            )
        )
    return findings


def analyze_launcher_log(text, label):
    findings = []
    if not text.strip():
        return findings
    if "Auto-connect config written" in text:
        ports = _sample(r"Auto-connect config written for ([^\s]+)", text)
        findings.append(("ok", "%s wrote auto-connect for: %s" % (label, ", ".join(ports) or "?")))
    if "Starting the game" in text and "Disconnected" in text:
        findings.append(
            (
                "info",
                "%s: lobby TCP client disconnects on Start (expected) - host UI "
                "must not treat that as 'session dead'" % label,
            )
        )
    join_port = _sample(r"Joining ([^\s]+)", text)
    host_port = _sample(r"Opening lobby on port (\d+)", text)
    if join_port:
        findings.append(("info", "%s join target: %s" % (label, ", ".join(join_port))))
    if host_port:
        findings.append(("info", "%s lobby port: %s" % (label, ", ".join(host_port))))
    return findings


def analyze_bundle(path, label):
    findings = []
    findings.append(("info", "--- %s: %s ---" % (label, path or "(none)")))
    if not path or not os.path.isdir(path):
        findings.append(("warn", "%s bundle not found" % label))
        return findings
    info = _read_text(os.path.join(path, "info.txt"))
    if info:
        for line in info.splitlines():
            if "runtime version" in line or "join target" in line or "lobby port" in line:
                findings.append(("info", line.strip()))
    findings.extend(analyze_launcher_log(_read_text(os.path.join(path, "launcher-log.txt")), label))
    findings.extend(analyze_client_log(_read_text(os.path.join(path, "game-client.log")), label))
    findings.extend(analyze_server_log(_read_text(os.path.join(path, "server-log.txt"))))
    return findings


def print_report(findings):
    icons = {"info": "-", "ok": "OK", "warn": "!!", "fail": "XX"}
    fails = 0
    warns = 0
    for kind, message in findings:
        print("%s %s" % (icons.get(kind, "-"), message))
        if kind == "fail":
            fails += 1
        elif kind == "warn":
            warns += 1
    print()
    if fails:
        print("Verdict: %s critical issue(s), %s warning(s)" % (fails, warns))
        return 2
    if warns:
        print("Verdict: no hard fails, %s warning(s)" % warns)
        return 1
    print("Verdict: nothing obviously broken in these logs")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--received", help="join/received diagnostic folder")
    parser.add_argument("--host-diag", help="host diagnostics folder")
    parser.add_argument("--client-log", help="extra live client.log path")
    parser.add_argument(
        "--list",
        action="store_true",
        help="list newest received/diagnostics folders and exit",
    )
    args = parser.parse_args(argv)

    if args.list:
        print("received root:", DEFAULT_RECEIVED)
        print("  newest:", _newest_dir(DEFAULT_RECEIVED) or "(none)")
        print("diagnostics root:", DEFAULT_DIAG)
        print("  newest:", _newest_dir(DEFAULT_DIAG) or "(none)")
        return 0

    received = args.received or _newest_dir(DEFAULT_RECEIVED)
    host_diag = args.host_diag or _newest_dir(DEFAULT_DIAG)

    findings = []
    findings.extend(analyze_bundle(host_diag, "host"))
    findings.extend(analyze_bundle(received, "join"))

    live = args.client_log or DEFAULT_CLIENT_LOG
    if live and os.path.isfile(live):
        findings.append(("info", "--- live client.log: %s ---" % live))
        findings.extend(analyze_client_log(_read_text(live), "live"))

    if len(findings) <= 2:
        print(
            "No diagnostic bundles found under:\n  %s\n  %s\n"
            "Export/Send-to-host from the launcher first, or pass --received / --host-diag."
            % (DEFAULT_RECEIVED, DEFAULT_DIAG),
            file=sys.stderr,
        )
        return 1
    return print_report(findings)


if __name__ == "__main__":
    sys.exit(main())
