"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path = require("path");
const child_process_1 = require("child_process");
let mainWindow = null;
let pythonProcess = null;
const isDev = process.env.NODE_ENV === 'development' || !electron_1.app.isPackaged;
function startPythonBackend() {
    if (isDev) {
        console.log("Development mode: Expecting FastAPI backend to be run externally via npm run backend:dev");
        return;
    }
    const scriptPath = path.join(process.resourcesPath, 'backend', 'main.py');
    const pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';
    pythonProcess = (0, child_process_1.spawn)(pythonExecutable, [scriptPath]);
    pythonProcess.stdout?.on('data', (data) => {
        console.log(`Python stdout: ${data}`);
    });
    pythonProcess.stderr?.on('data', (data) => {
        console.error(`Python stderr: ${data}`);
    });
    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
    });
}
function createWindow() {
    mainWindow = new electron_1.BrowserWindow({
        width: 1280,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
        },
        show: false,
        backgroundColor: '#0f172a'
    });
    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
        mainWindow.webContents.openDevTools();
    }
    else {
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }
    mainWindow.once('ready-to-show', () => {
        mainWindow?.show();
    });
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}
electron_1.app.whenReady().then(() => {
    startPythonBackend();
    createWindow();
    electron_1.app.on('activate', () => {
        if (electron_1.BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});
electron_1.app.on('window-all-closed', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
    if (process.platform !== 'darwin') {
        electron_1.app.quit();
    }
});
