#!/usr/bin/env python3
"""
Waizen — apply your config.json to the template.

Replaces the {{PLACEHOLDERS}} across the project files with the values from
config.json, so the panel/agent show YOUR business details.

Usage:
    cp config.example.json config.json   # then edit config.json
    python3 setup.py
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
cfg_path = ROOT / "config.json"
if not cfg_path.exists():
    print("✗ config.json not found.\n  → cp config.example.json config.json   (then edit it)")
    sys.exit(1)

cfg  = json.loads(cfg_path.read_text(encoding="utf-8"))
b    = cfg.get("business", {})
bank = b.get("bank", {})
ag   = cfg.get("agent", {})
phones = list(b.get("phones", [])) + ["", ""]
emails = list(b.get("emails", [])) + ["", ""]

MAP = {
    "{{BUSINESS_NAME}}":    b.get("name", "Mi Empresa"),
    "{{BUSINESS_LEGAL}}":   bank.get("holder", b.get("name", "Mi Empresa")),
    "{{BUSINESS_ADDRESS}}": b.get("address", ""),
    "{{PHONE_1}}":          phones[0],
    "{{PHONE_2}}":          phones[1],
    "{{EMAIL_1}}":          emails[0],
    "{{EMAIL_2}}":          emails[1],
    "{{WEBSITE}}":          b.get("website", ""),
    "{{BANK_NAME}}":        bank.get("name", ""),
    "{{BANK_ACCOUNT}}":     str(bank.get("account_number", "")),
    "{{BANK_NIT}}":         str(bank.get("nit", "")),
    "{{SIGNATURE_NAME}}":   b.get("signature_name", ""),
    "{{AGENT_NAME}}":       ag.get("display_name", "Asistente"),
    "{{WHATSAPP_ACCOUNT}}": ag.get("whatsapp_account", "mybiz"),
}

# These are deployment/environment specific — set them in .env or during deploy.
DEPLOY = ["{{HOST}}", "{{HOST_TAILSCALE}}", "{{WORKSPACE}}",
          "{{DASHBOARD_DIR}}", "{{PDFGEN_DIR}}", "{{GOOGLE_API_KEY}}", "{{AUTH_HASH}}"]

DIRS = ["dashboard", "api", "agent", "pdfgen", "infra"]
EXT  = {".html", ".js", ".py", ".md", ".json", ".yml", ".yaml", ".service", ""}

changed = 0
for d in DIRS:
    for f in (ROOT / d).rglob("*"):
        if not f.is_file() or f.suffix.lower() not in EXT:
            continue
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = t
        for k, v in MAP.items():
            new = new.replace(k, v)
        if new != t:
            f.write_text(new, encoding="utf-8")
            changed += 1

print(f"✓ Applied your config to {changed} files.")

remaining = set()
for d in DIRS:
    for f in (ROOT / d).rglob("*"):
        if f.is_file() and f.suffix.lower() in EXT:
            try:
                t = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for p in DEPLOY:
                if p in t:
                    remaining.add(p)
if remaining:
    print("\n⚠ Deployment-specific placeholders still present (set these when you deploy):")
    for p in sorted(remaining):
        print("   ", p)

print("\nNext steps → docs/SETUP.md")
