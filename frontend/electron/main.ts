import { app, BrowserWindow, Notification, shell } from 'electron';
import { autoUpdater } from 'electron-updater';
import * as path from 'path';
import * as net from 'net';
import * as http from 'http';
import { spawn, ChildProcess } from 'child_process';

let mainWindow: BrowserWindow | null = null;
let backend: ChildProcess | null = null;

const isDev = !app.isPackaged;

if (!app.requestSingleInstanceLock()) app.quit();

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address() as net.AddressInfo;
      srv.close(() => resolve(port));
    });
    srv.on('error', reject);
  });
}

function waitForBackend(url: string, timeoutMs = 60000): Promise<void> {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = () => {
      http.get(url, (res) => {
        res.resume();
        if (res.statusCode === 200) return resolve();
        retry();
      }).on('error', retry);
    };
    const retry = () => (Date.now() - start > timeoutMs ? reject(new Error('Backend timeout')) : setTimeout(attempt, 300));
    attempt();
  });
}

// Lance le serveur Python embarqué (PyInstaller) qui sert l'API et l'interface
async function startBackend(): Promise<string> {
  const port = await freePort();
  const exe = path.join(process.resourcesPath, 'backend', process.platform === 'win32' ? 'stockpulse-backend.exe' : 'stockpulse-backend');
  backend = spawn(exe, [], {
    env: {
      ...process.env,
      PORT: String(port),
      STOCKPULSE_DATA_DIR: app.getPath('userData'),
      STOCKPULSE_FRONTEND: path.join(process.resourcesPath, 'frontend'),
      STOCKPULSE_VERSION: app.getVersion(),
    },
    windowsHide: true,
  });
  backend.stdout?.on('data', (d) => console.log(`[backend] ${d}`));
  backend.stderr?.on('data', (d) => console.error(`[backend] ${d}`));
  const url = `http://127.0.0.1:${port}`;
  await waitForBackend(`${url}/api/health`);
  watchHealth(url);
  return url;
}

// Vérificateur d'état : notification Windows dès qu'un contrôle se dégrade (toutes les 15 min)
const RANK: Record<string, number> = { ok: 0, warn: 1, error: 2 };
function watchHealth(url: string) {
  let previous: Record<string, string> = {};
  const check = () => http.get(`${url}/api/health/full?refresh=true`, (res) => {
    let body = '';
    res.on('data', (c) => (body += c));
    res.on('end', () => {
      try {
        const report = JSON.parse(body) as { checks: { id: string; status: string; detail: string }[] };
        const worse = report.checks.filter((c) => previous[c.id] !== undefined && RANK[c.status] > RANK[previous[c.id]]);
        if (worse.length && Notification.isSupported()) {
          new Notification({ title: 'StockPulse : état dégradé', body: worse.map((c) => c.detail).join('\n') }).show();
        }
        previous = Object.fromEntries(report.checks.map((c) => [c.id, c.status]));
      } catch { /* rapport illisible : nouvel essai au prochain passage */ }
    });
  }).on('error', () => {});
  setTimeout(check, 60000);
  setInterval(check, 15 * 60000);
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#020617',
    autoHideMenuBar: true,
    icon: path.join(__dirname, '..', 'assets', 'icon.png'),
    webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true },
  });

  // Les liens d'articles s'ouvrent dans le navigateur par défaut
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) shell.openExternal(url);
    return { action: 'deny' };
  });
  mainWindow.on('closed', () => { mainWindow = null; });

  if (isDev) {
    await mainWindow.loadURL('http://127.0.0.1:5173');
    return;
  }
  await mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(
    '<body style="background:#020617;color:#94a3b8;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">StockPulse…</body>')}`);
  try {
    await mainWindow.loadURL(await startBackend());
  } catch (e) {
    await mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(
      `<body style="background:#020617;color:#f43f5e;font-family:sans-serif;padding:40px">Impossible de démarrer le moteur StockPulse : ${String(e)}</body>`)}`);
  }
}

app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

app.setAppUserModelId('com.stockpulse.desktop');

app.whenReady().then(() => {
  createWindow();
  // Mises à jour automatiques depuis les releases GitHub (téléchargement en arrière-plan, installation à la fermeture)
  if (!isDev) autoUpdater.checkForUpdatesAndNotify().catch(() => {});
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('window-all-closed', () => {
  app.quit();
});

app.on('will-quit', () => {
  backend?.kill();
});
