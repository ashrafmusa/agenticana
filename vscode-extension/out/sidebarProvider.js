"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgenticanaSidebarProvider = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const child_process_1 = require("child_process");
const util_1 = require("util");
const execAsync = (0, util_1.promisify)(child_process_1.exec);
class AgenticanaSidebarProvider {
    constructor(_extensionUri) {
        this._extensionUri = _extensionUri;
    }
    resolveWebviewView(webviewView, _context, _token) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };
        webviewView.webview.html = this._getHtmlContent(webviewView.webview);
        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'runCommand':
                    await vscode.commands.executeCommand(msg.vscodeCommand);
                    break;
                case 'getState':
                    await this._sendState(webviewView.webview);
                    break;
                case 'openTerminal':
                    this._runScript(msg.script, msg.label);
                    break;
            }
        });
        // Send initial state after a short delay (let the UI settle)
        setTimeout(() => this._sendState(webviewView.webview), 800);
    }
    refresh() {
        if (this._view) {
            this._sendState(this._view.webview);
        }
    }
    _getProjectRoot() {
        const cfg = vscode.workspace.getConfiguration('agenticana');
        const custom = cfg.get('projectRoot', '');
        if (custom)
            return custom;
        const wf = vscode.workspace.workspaceFolders;
        return wf && wf.length > 0 ? wf[0].uri.fsPath : '';
    }
    _getPython() {
        return vscode.workspace.getConfiguration('agenticana').get('pythonPath', 'python');
    }
    _runScript(script, label) {
        const root = this._getProjectRoot();
        const term = vscode.window.createTerminal({ name: `Agenticana — ${label}`, cwd: root });
        term.show();
        term.sendText(script);
    }
    async _sendState(webview) {
        const root = this._getProjectRoot();
        const py = this._getPython();
        // Guardian status
        let guardianActive = false;
        const hookPath = path.join(root, '.git', 'hooks', 'pre-commit');
        try {
            const content = fs.readFileSync(hookPath, 'utf-8');
            guardianActive = content.includes('Guardian');
        }
        catch { }
        // Latest attestation
        let attestation = {};
        try {
            const attestPath = path.join(root, '.Agentica', 'attestations', 'latest.json');
            attestation = JSON.parse(fs.readFileSync(attestPath, 'utf-8'));
        }
        catch { }
        // Evolution log — last cycle
        let lastEvolution = {};
        try {
            const evPath = path.join(root, '.Agentica', 'evolution_log.json');
            const ev = JSON.parse(fs.readFileSync(evPath, 'utf-8'));
            const cycles = ev.cycles || [];
            lastEvolution = cycles[cycles.length - 1] || {};
        }
        catch { }
        // Competitor intel — gap count
        let gapCount = 0;
        try {
            const intelPath = path.join(root, '.Agentica', 'competitor_intel.json');
            const intel = JSON.parse(fs.readFileSync(intelPath, 'utf-8'));
            gapCount = intel.reduce((sum, r) => sum + (r.trending_requests?.length || 0), 0);
        }
        catch { }
        // Recent guardian audit logs
        let recentAudits = [];
        try {
            const logDir = path.join(root, '.Agentica', 'logs', 'guardian');
            if (fs.existsSync(logDir)) {
                recentAudits = fs.readdirSync(logDir)
                    .filter(f => f.endsWith('.json'))
                    .sort().reverse().slice(0, 3)
                    .map(f => {
                    try {
                        return JSON.parse(fs.readFileSync(path.join(logDir, f), 'utf-8'));
                    }
                    catch {
                        return null;
                    }
                })
                    .filter(Boolean);
            }
        }
        catch { }
        webview.postMessage({
            command: 'updateState',
            state: {
                guardianActive,
                attestation,
                lastEvolution,
                gapCount,
                recentAudits,
                projectRoot: root,
                timestamp: new Date().toISOString(),
            }
        });
    }
    _getHtmlContent(webview) {
        return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';"/>
<title>Agenticana</title>
<style>
  :root {
    --gap: 10px;
    --radius: 8px;
    --green:  #4ade80;
    --yellow: #fbbf24;
    --red:    #f87171;
    --blue:   #60a5fa;
    --purple: #a78bfa;
    --bg-card: rgba(255,255,255,0.04);
    --border:  rgba(255,255,255,0.08);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    background: var(--vscode-sideBar-background);
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: var(--gap);
    min-height: 100vh;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 4px 4px;
  }
  .header .logo { font-size: 24px; line-height: 1; }
  .header .title { font-size: 15px; font-weight: 700; letter-spacing: -0.3px; }
  .header .subtitle { font-size: 11px; opacity: 0.55; }

  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 12px;
  }
  .card-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    opacity: 0.5;
    margin-bottom: 8px;
  }

  /* Status badges */
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge.green  { background: rgba(74,222,128,0.12); color: var(--green);  border: 1px solid rgba(74,222,128,0.25); }
  .badge.yellow { background: rgba(251,191,36,0.12); color: var(--yellow); border: 1px solid rgba(251,191,36,0.25); }
  .badge.red    { background: rgba(248,113,113,0.12); color: var(--red);   border: 1px solid rgba(248,113,113,0.25); }
  .badge.blue   { background: rgba(96,165,250,0.12); color: var(--blue);   border: 1px solid rgba(96,165,250,0.25); }
  .badge .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

  /* Buttons */
  .btn-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }
  .btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    padding: 7px 8px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg-card);
    color: var(--vscode-foreground);
    cursor: pointer;
    font-size: 11px;
    font-weight: 500;
    transition: background 0.15s, border-color 0.15s;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .btn:hover { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.2); }
  .btn.primary { background: rgba(96,165,250,0.12); border-color: rgba(96,165,250,0.3); color: var(--blue); }
  .btn.primary:hover { background: rgba(96,165,250,0.22); }
  .btn.success { background: rgba(74,222,128,0.1); border-color: rgba(74,222,128,0.3); color: var(--green); }
  .btn.danger  { background: rgba(248,113,113,0.1); border-color: rgba(248,113,113,0.3); color: var(--red); }
  .btn.full    { grid-column: span 2; }
  .btn .icon   { font-size: 13px; flex-shrink: 0; }

  /* NL Swarm input */
  .nl-form { display: flex; gap: 6px; }
  .nl-form input {
    flex: 1;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 8px;
    color: var(--vscode-foreground);
    font-size: 12px;
    outline: none;
  }
  .nl-form input::placeholder { opacity: 0.4; }
  .nl-form input:focus { border-color: rgba(96,165,250,0.5); }
  .nl-form button {
    padding: 6px 10px;
    background: rgba(96,165,250,0.2);
    border: 1px solid rgba(96,165,250,0.4);
    border-radius: 6px;
    color: var(--blue);
    cursor: pointer;
    font-size: 13px;
  }
  .nl-form button:hover { background: rgba(96,165,250,0.35); }

  /* Status rows */
  .status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
    font-size: 11.5px;
  }
  .status-row:last-child { border-bottom: none; }
  .status-row .label { opacity: 0.7; }

  /* Audit log */
  .audit-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 11px;
    opacity: 0.85;
  }
  .audit-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

  /* Trust score bar */
  .trust-bar-wrap { margin-top: 6px; }
  .trust-bar-label { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; }
  .trust-bar { height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden; }
  .trust-bar-fill { height: 100%; border-radius: 2px; transition: width 0.4s; }

  .divider { height: 1px; background: var(--border); }
  .muted { font-size: 11px; opacity: 0.45; text-align: center; padding: 4px 0; }

  .spin { animation: spin 1s linear infinite; display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<div class="header">
  <div class="logo">🦅</div>
  <div>
    <div class="title">Agenticana</div>
    <div class="subtitle">Sovereign AI Developer OS</div>
  </div>
</div>

<!-- Guardian Status -->
<div class="card" id="guardian-card">
  <div class="card-title">⚔️ Guardian Mode</div>
  <div class="status-row">
    <span class="label">Pre-commit hook</span>
    <span class="badge yellow" id="guardian-badge"><span class="dot"></span> Loading…</span>
  </div>
  <div class="status-row">
    <span class="label">Custom YAML rules</span>
    <span id="rules-status" class="muted">—</span>
  </div>
  <div style="margin-top:8px; display:flex; gap:6px;">
    <button class="btn success" onclick="runCmd('agenticana.guardianStatus')">
      <span class="icon">🛡️</span> Status
    </button>
    <button class="btn" onclick="runScript('python scripts/guardian_mode.py install', 'Guardian Install')">
      <span class="icon">⚡</span> Install
    </button>
    <button class="btn" onclick="runScript('python scripts/guardian_rules_engine.py list', 'Rules List')">
      <span class="icon">📋</span> Rules
    </button>
  </div>
</div>

<!-- NL Swarm -->
<div class="card">
  <div class="card-title">🔀 NL Swarm — Plain English</div>
  <div class="nl-form">
    <input type="text" id="nl-input" placeholder='e.g. "Add auth and write tests"' />
    <button onclick="dispatchNLSwarm()" title="Dispatch Swarm">▶</button>
  </div>
  <div style="margin-top:6px; display:flex; gap:6px;">
    <button class="btn primary" onclick="dispatchNLSwarm(true)" style="flex:1;">
      <span class="icon">🚀</span> Generate + Run
    </button>
    <button class="btn" onclick="dispatchNLSwarm(false)" style="flex:1;">
      <span class="icon">📄</span> Manifest only
    </button>
  </div>
</div>

<!-- Proof-of-Work -->
<div class="card" id="pow-card">
  <div class="card-title">✅ Proof-of-Work</div>
  <div class="trust-bar-wrap">
    <div class="trust-bar-label">
      <span>Trust Score</span>
      <span id="trust-score-text" style="font-weight:600;">—</span>
    </div>
    <div class="trust-bar">
      <div class="trust-bar-fill" id="trust-bar" style="width:0%; background: var(--green);"></div>
    </div>
  </div>
  <div class="status-row" style="margin-top:8px;">
    <span class="label">Last debate</span>
    <span id="pow-debate">—</span>
  </div>
  <div class="status-row">
    <span class="label">Guardian check</span>
    <span id="pow-guardian">—</span>
  </div>
  <button class="btn primary full" onclick="runCmd('agenticana.powSign')" style="margin-top:8px;">
    <span class="icon">🔏</span> Sign Commit (Proof-of-Work)
  </button>
</div>

<!-- Sovereign Loop -->
<div class="card">
  <div class="card-title">🦅 Sovereign Loop (P25)</div>
  <div class="status-row">
    <span class="label">Last phase evolved</span>
    <span id="last-phase">—</span>
  </div>
  <div class="status-row">
    <span class="label">Competitor gaps tracked</span>
    <span id="gap-count" class="badge blue"><span class="dot"></span> —</span>
  </div>
  <div class="btn-grid" style="margin-top:8px;">
    <button class="btn" onclick="runCmd('agenticana.sovereignScan')">
      <span class="icon">👁️</span> Scan Competitors
    </button>
    <button class="btn primary" onclick="runCmd('agenticana.sovereignEvolve')">
      <span class="icon">🧬</span> Self-Evolve
    </button>
  </div>
</div>

<!-- Recent Audits -->
<div class="card">
  <div class="card-title">📋 Recent Guardian Audits</div>
  <div id="audit-list"><div class="muted">No audits yet. Make a commit to start.</div></div>
</div>

<!-- Quick Actions -->
<div class="card">
  <div class="card-title">⚡ Quick Actions</div>
  <div class="btn-grid">
    <button class="btn" onclick="runScript('python scripts/agentica_cli.py pulse', 'Performance Pulse')">
      <span class="icon">📊</span> Pulse
    </button>
    <button class="btn" onclick="runScript('python scripts/agentica_cli.py sentinel', 'Sentinel')">
      <span class="icon">🔧</span> Sentinel
    </button>
    <button class="btn" onclick="runCmd('agenticana.openDashboard')">
      <span class="icon">🖥️</span> Dashboard
    </button>
    <button class="btn" onclick="runScript('python scripts/reasoning_bank.py stats', 'ReasoningBank')">
      <span class="icon">🧠</span> Memory
    </button>
    <button class="btn full" onclick="runScript('python scripts/agentica_cli.py simulacrum &quot;How to improve this codebase?&quot;', 'Simulacrum Debate')">
      <span class="icon">🎭</span> Start Simulacrum Debate
    </button>
  </div>
</div>

<div class="muted" id="last-refresh">Last refresh: —</div>

<script>
  const vscode = acquireVsCodeApi();

  function runCmd(cmd) {
    vscode.postMessage({ command: 'runCommand', vscodeCommand: cmd });
  }

  function runScript(script, label) {
    vscode.postMessage({ command: 'openTerminal', script, label });
  }

  function dispatchNLSwarm(autoRun) {
    const input = document.getElementById('nl-input').value.trim();
    if (!input) {
      // Fall back to command palette flow
      runCmd('agenticana.runNLSwarm');
      return;
    }
    const runFlag = autoRun ? ' --run' : '';
    const script = 'python scripts/nl_swarm.py "' + input.replace(/"/g, '\\"') + '"' + runFlag;
    runScript(script, 'NL Swarm');
  }

  // Enter key in NL input → dispatch
  document.getElementById('nl-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') dispatchNLSwarm(false);
  });

  // Request state on load
  vscode.postMessage({ command: 'getState' });

  // Handle state updates from extension host
  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg.command !== 'updateState') return;
    const s = msg.state;

    // Guardian badge
    const badge = document.getElementById('guardian-badge');
    if (s.guardianActive) {
      badge.className = 'badge green';
      badge.innerHTML = '<span class="dot"></span> ACTIVE';
    } else {
      badge.className = 'badge yellow';
      badge.innerHTML = '<span class="dot"></span> INACTIVE';
    }

    // Rules status
    document.getElementById('rules-status').textContent =
      s.guardianActive ? 'P24 rules enabled' : 'Run: guardian install';

    // Trust score
    const ts = s.attestation?.trust_score || '';
    document.getElementById('trust-score-text').textContent = ts || '—';
    const numeric = ts ? parseInt(ts.split('/')[0], 10) : 0;
    const bar = document.getElementById('trust-bar');
    bar.style.width = numeric + '%';
    bar.style.background = numeric >= 70 ? 'var(--green)' : numeric >= 40 ? 'var(--yellow)' : 'var(--red)';

    // PoW details
    const debate = s.attestation?.debate;
    document.getElementById('pow-debate').textContent =
      debate?.debated ? ('✓ ' + (debate.session_id || '').substring(0, 8)) : '—';
    const guardian = s.attestation?.guardian;
    document.getElementById('pow-guardian').textContent =
      guardian?.passed ? '✓ PASSED' : guardian?.ran ? '✗ FAILED' : '—';

    // Sovereign loop
    document.getElementById('last-phase').textContent =
      s.lastEvolution?.phase ? (s.lastEvolution.phase + ' — ' + (s.lastEvolution.name || '').substring(0, 25)) : '—';
    const gapBadge = document.getElementById('gap-count');
    gapBadge.innerHTML = '<span class="dot"></span> ' + (s.gapCount || 0) + ' gaps tracked';

    // Audit log
    const audits = s.recentAudits || [];
    const auditEl = document.getElementById('audit-list');
    if (audits.length === 0) {
      auditEl.innerHTML = '<div class="muted">No audits yet. Make a commit to start.</div>';
    } else {
      auditEl.innerHTML = audits.map(a => {
        const color = a.blocked ? 'var(--red)' : 'var(--green)';
        const label = a.blocked ? 'BLOCKED' : 'APPROVED';
        const ts = (a.timestamp || '').replace('T', ' ').substring(0, 16);
        return \`<div class="audit-item">
          <div class="audit-dot" style="background:\${color}"></div>
          <span style="flex:1;opacity:0.7;">\${ts}</span>
          <span style="color:\${color};font-weight:600;">\${label}</span>
        </div>\`;
      }).join('');
    }

    // Last refresh
    document.getElementById('last-refresh').textContent =
      'Last refresh: ' + new Date().toLocaleTimeString();
  });
</script>
</body>
</html>`;
    }
}
exports.AgenticanaSidebarProvider = AgenticanaSidebarProvider;
AgenticanaSidebarProvider.viewType = 'agenticana.sidebarView';
//# sourceMappingURL=sidebarProvider.js.map