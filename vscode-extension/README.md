# Agenticana VS Code Extension 🦅

**P23 — Sovereign AI Developer OS, now in your sidebar.**

Brings the full Agenticana command surface directly into VS Code — no terminal required.

---

## Features

| Feature | Description |
|---------|-------------|
| 🛡️ **Guardian Status** | Live badge showing if the pre-commit hook is active |
| 🔀 **NL Swarm** | Type plain English → dispatch a multi-agent swarm inline |
| ✅ **Trust Score** | Visual progress bar for your latest Proof-of-Work attestation |
| 🦅 **Sovereign Loop** | One-click competitor scan + self-evolve buttons |
| 📋 **Audit Log** | Last 3 Guardian pre-commit results at a glance |
| ⚡ **Quick Actions** | Pulse, Sentinel, Dashboard, Memory — one click each |

---

## Installation

### Development Mode (recommended for local use)

```bash
cd vscode-extension
npm install
npm run compile
```

Then in VS Code: press **F5** → this opens an Extension Development Host with the sidebar active.

### Package as VSIX

```bash
cd vscode-extension
npm install -g @vscode/vsce   # one-time
npm run compile
vsce package
# Produces: agenticana-1.0.0.vsix
```

Install in VS Code: `Extensions → ⋯ → Install from VSIX…`

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `agenticana.projectRoot` | *(workspace root)* | Override the Agenticana project root |
| `agenticana.pythonPath` | `python` | Python executable path |
| `agenticana.dashboardPort` | `8080` | Flask dashboard port |
| `agenticana.githubToken` | *(empty)* | GitHub token for Sovereign Intel (P25) |

---

## Commands

All commands are accessible from the Command Palette (`Ctrl+Shift+P` → search "Agenticana"):

- `Agenticana: Open Sidebar`
- `Agenticana: Run NL Swarm`
- `Agenticana: Check Guardian Status`
- `Agenticana: Scan Competitors (Sovereign Intel)`
- `Agenticana: Self-Evolve (Sovereign Loop)`
- `Agenticana: Open Web Dashboard`
- `Agenticana: Sign Commit (Proof-of-Work)`
- `Agenticana: Refresh Sidebar`

---

## Architecture

```
vscode-extension/
├── src/
│   ├── extension.ts        ← activation, command registration
│   └── sidebarProvider.ts  ← WebviewViewProvider + HTML UI
├── media/
│   └── icon.svg            ← activity bar icon
├── package.json            ← VS Code extension manifest
├── tsconfig.json
└── .vscodeignore
```

The sidebar reads state directly from `.Agentica/` JSON files (attestations, logs, evolution log, competitor intel) — **no server required** for the sidebar to display information.

Commands open integrated terminals that run the existing Python scripts, keeping the extension lightweight and always in sync with the CLI.

---

*Secretary Bird: always watching, always ready. 🦅*
