import * as vscode from 'vscode';
import * as path from 'path';
import { AgenticanaSidebarProvider } from './sidebarProvider';

export function activate(context: vscode.ExtensionContext) {
    console.log('🦅 Agenticana extension activated');

    // ── Register sidebar ──────────────────────────────────────────────────────
    const sidebarProvider = new AgenticanaSidebarProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            'agenticana.sidebarView',
            sidebarProvider,
            { webviewOptions: { retainContextWhenHidden: true } }
        )
    );

    // ── Helper: resolve project root ──────────────────────────────────────────
    function getProjectRoot(): string {
        const cfg = vscode.workspace.getConfiguration('agenticana');
        const customRoot = cfg.get<string>('projectRoot', '');
        if (customRoot) return customRoot;
        const wf = vscode.workspace.workspaceFolders;
        return wf && wf.length > 0 ? wf[0].uri.fsPath : '';
    }

    function getPython(): string {
        return vscode.workspace.getConfiguration('agenticana').get<string>('pythonPath', 'python');
    }

    // ── Helper: run a script in terminal ─────────────────────────────────────
    function runInTerminal(label: string, cmd: string, cwd?: string) {
        const terminal = vscode.window.createTerminal({ name: `Agenticana — ${label}`, cwd });
        terminal.show();
        terminal.sendText(cmd);
    }

    // ── Commands ──────────────────────────────────────────────────────────────

    context.subscriptions.push(
        vscode.commands.registerCommand('agenticana.openSidebar', () => {
            vscode.commands.executeCommand('agenticana.sidebarView.focus');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('agenticana.refresh', () => {
            sidebarProvider.refresh();
            vscode.window.showInformationMessage('🦅 Agenticana sidebar refreshed.');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('agenticana.guardianStatus', async () => {
            const root = getProjectRoot();
            const py = getPython();
            runInTerminal('Guardian Status', `${py} scripts/guardian_mode.py status`, root);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('agenticana.runNLSwarm', async () => {
            const prompt = await vscode.window.showInputBox({
                title: '🦅 NL Swarm — Plain English to Agent Dispatch',
                prompt: 'Describe what you want to build, audit, or test...',
                placeHolder: 'e.g. Add authentication to the API and write tests for it',
            });
            if (!prompt) return;

            const run = await vscode.window.showQuickPick(['Generate manifest only', 'Generate + dispatch swarm'], {
                title: 'NL Swarm mode',
            });
            if (!run) return;

            const root = getProjectRoot();
            const py = getPython();
            const dispatch = run.includes('dispatch') ? ' --run' : '';
            const cmd = `${py} scripts/nl_swarm.py "${prompt.replace(/"/g, '\\"')}"${dispatch}`;
            runInTerminal('NL Swarm', cmd, root);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('agenticana.sovereignScan', async () => {
            const root = getProjectRoot();
            const py = getPython();
            const cfg = vscode.workspace.getConfiguration('agenticana');
            const token = cfg.get<string>('githubToken', '');
            const tokenFlag = token ? ` --token "${token}"` : '';
            runInTerminal('Sovereign Intel Scan', `${py} scripts/sovereign_intel.py${tokenFlag}`, root);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('agenticana.sovereignEvolve', async () => {
            const mode = await vscode.window.showQuickPick(
                ['Full evolve (commit + push)', 'Evolve without push (--no-push)', 'Dry run only'],
                { title: '🦅 Sovereign Loop — Select mode' }
            );
            if (!mode) return;

            const root = getProjectRoot();
            const py = getPython();
            let flags = '';
            if (mode.includes('Dry run')) flags = ' --dry-run';
            else if (mode.includes('without push')) flags = ' --no-push';

            runInTerminal('Sovereign Loop', `${py} scripts/sovereign_loop.py${flags}`, root);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('agenticana.powSign', async () => {
            const root = getProjectRoot();
            const py = getPython();
            runInTerminal('Proof-of-Work Sign', `${py} scripts/pow_commit.py sign`, root);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('agenticana.openDashboard', async () => {
            const cfg = vscode.workspace.getConfiguration('agenticana');
            const port = cfg.get<number>('dashboardPort', 8080);
            const url = `http://127.0.0.1:${port}`;
            const choice = await vscode.window.showInformationMessage(
                `Open Agenticana Dashboard at ${url}?`,
                'Open in Browser',
                'Start Dashboard Server'
            );
            if (choice === 'Open in Browser') {
                vscode.env.openExternal(vscode.Uri.parse(url));
            } else if (choice === 'Start Dashboard Server') {
                const root = getProjectRoot();
                const py = getPython();
                runInTerminal('Dashboard Server', `${py} scripts/dashboard_api.py`, root);
                setTimeout(() => vscode.env.openExternal(vscode.Uri.parse(url)), 2000);
            }
        })
    );

    vscode.window.showInformationMessage('🦅 Agenticana is ready. Open the sidebar to get started.');
}

export function deactivate() {
    console.log('Agenticana extension deactivated.');
}
