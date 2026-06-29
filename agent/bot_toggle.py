#!/usr/bin/env python3
"""Pausa/reanuda {{AGENT_NAME}} (cuenta {{WHATSAPP_ACCOUNT}}) en el VPS via dmPolicy + restart gateway.
Uso: alby_toggle.py [status|pause|play|toggle]  -> imprime PAUSED|ACTIVE
"""
import json, sys, subprocess, os

CFG = "/home/ubuntu/.openclaw/openclaw.json"
ACCOUNT = "{{WHATSAPP_ACCOUNT}}"
PAUSE_VAL = "disabled"
PLAY_VAL = "open"


def load():
    with open(CFG, encoding="utf-8") as f:
        return json.load(f)


def save(d):
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)


def acct(d):
    return d.setdefault("channels", {}).setdefault("whatsapp", {}).setdefault("accounts", {}).setdefault(ACCOUNT, {})


def is_paused(d):
    return acct(d).get("dmPolicy") == PAUSE_VAL


def set_dm(d, val):
    a = acct(d)
    a["dmPolicy"] = val
    if val == PLAY_VAL:
        a.setdefault("allowFrom", ["*"])  # open requiere allowFrom


def restart_gateway():
    env = dict(os.environ)
    env.setdefault("XDG_RUNTIME_DIR", "/run/user/%d" % os.getuid())
    subprocess.run(["systemctl", "--user", "restart", "openclaw-gateway.service"],
                   env=env, check=False, capture_output=True)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    d = load()
    if action == "status":
        print("PAUSED" if is_paused(d) else "ACTIVE")
    elif action == "pause":
        set_dm(d, PAUSE_VAL); save(d); restart_gateway(); print("PAUSED")
    elif action == "play":
        set_dm(d, PLAY_VAL); save(d); restart_gateway(); print("ACTIVE")
    elif action == "toggle":
        if is_paused(d):
            set_dm(d, PLAY_VAL); save(d); restart_gateway(); print("ACTIVE")
        else:
            set_dm(d, PAUSE_VAL); save(d); restart_gateway(); print("PAUSED")
    else:
        print("usage: status|pause|play|toggle")


if __name__ == "__main__":
    main()
