const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('mockDesktop', Object.freeze({
  saveConnection: config => ipcRenderer.invoke('connection:save', config),
  version: () => ipcRenderer.invoke('app:version'),
}));
