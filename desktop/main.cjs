const { app, BrowserWindow, ipcMain, safeStorage, dialog } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const { SettingsStore, allowedSender } = require('./settings-store.cjs');

let window, backend, store, profiles={}, quitting=false;
const lock=app.requestSingleInstanceLock();
if(!lock) app.quit();
else {
  app.on('second-instance',()=>{if(window){if(window.isMinimized())window.restore();window.focus();}});
  app.whenReady().then(start).catch(()=>{
    dialog.showErrorBox('启动失败','模拟引擎未能启动。请确认完整解压安装包；数据库连接可在应用启动后配置。');
    app.exit(1);
  });
}

function engineCommand() {
  if(app.isPackaged) return {exe:path.join(process.resourcesPath,'engine',process.platform==='win32'?'mock-source-engine.exe':'mock-source-engine'),args:[]};
  return {exe:process.env.MOCK_PYTHON || 'python',args:[path.join(__dirname,'../engine/desktop_entry.py')]};
}

async function launchBackend() {
  const command=engineCommand();
  const env={...process.env,PYTHONUTF8:'1'};delete env.SIGNAL_SIM_DB_PASSWORD;
  const child=spawn(command.exe,command.args,{stdio:['pipe','pipe','pipe'],windowsHide:true,env});
  // Keep stdin open: EOF is the engine's parent-death signal.
  child.stdin.on('error',()=>{});child.stdin.write(JSON.stringify({profiles})+'\n');
  const lines=readline.createInterface({input:child.stdout});
  return new Promise((resolve,reject)=>{
    let ready=false;
    const timer=setTimeout(()=>{child.kill();reject(new Error('Engine startup timed out'));},30000);
    child.on('error',()=>{clearTimeout(timer);reject(new Error('Engine executable unavailable'));});
    child.on('exit',()=>{
      if(!ready){clearTimeout(timer);reject(new Error('Engine exited before readiness'));}
      else if(!quitting){dialog.showErrorBox('模拟引擎已退出','应用将关闭。已提交的数据保留在数据库中，请重新打开后连接。');app.exit(1);}
    });
    lines.on('line',line=>{
      try {
        const data=JSON.parse(line);
        if(data.event!=='ready'||!/^http:\/\/127\.0\.0\.1:[1-9][0-9]{0,4}$/.test(data.url)||!data.token)return;
        ready=true;clearTimeout(timer);resolve({child,url:data.url,token:data.token});
      } catch { /* No arbitrary engine stdout is shown or persisted. */ }
    });
    child.stderr.on('data',()=>{});
  });
}

async function request(route,body) {
  const response=await fetch(backend.url+route,{method:'POST',headers:{'Content-Type':'application/json','Origin':backend.url,'X-Simulator-Token':backend.token},body:JSON.stringify(body),signal:AbortSignal.timeout(30000)});
  const value=await response.json();if(!response.ok)throw new Error(value.error||'操作未完成');return value;
}

async function start() {
  store=new SettingsStore(path.join(app.getPath('userData'),'connections.json'),safeStorage);
  try{profiles=store.load();}catch{profiles={};}
  backend=await launchBackend();
  ipcMain.handle('app:version',event=>{if(!allowedSender(event.senderFrame?.url,backend.url))throw new Error('来源不正确');return app.getVersion();});
  ipcMain.handle('connection:save',async(event,body)=>{
    if(!allowedSender(event.senderFrame?.url,backend.url))throw new Error('来源不正确');
    const {rememberPassword,...candidate}=body;
    const prior=profiles[candidate.engine];
    const same=prior && ['engine','host','port','database','user'].every(k=>prior[k]===candidate[k]);
    if(candidate.reusePassword && !candidate.password && same)candidate.password=prior.password;
    const value=await request('/api/connection/save',candidate);
    delete candidate.reusePassword;profiles[candidate.engine]=candidate;
    try{store.save(candidate,rememberPassword===true);return {...value,remembered:rememberPassword===true};}
    catch{return {...value,remembered:false,warning:'连接已在本次会话生效；本机配置未能保存，重新打开时请再次填写。'};}
  });
  window=new BrowserWindow({width:1280,height:940,minWidth:920,minHeight:720,title:'增量数据源模拟器',backgroundColor:'#f5f7fb',show:false,autoHideMenuBar:true,
    webPreferences:{preload:path.join(__dirname,'preload.cjs'),nodeIntegration:false,contextIsolation:true,sandbox:true}});
  window.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  window.webContents.session.setPermissionRequestHandler((_contents,_permission,callback)=>callback(false));
  window.webContents.on('will-navigate',(event,url)=>{if(!allowedSender(url,backend.url))event.preventDefault();});
  window.once('ready-to-show',()=>window.show());
  await window.loadURL(backend.url+'/');
}

app.on('window-all-closed',()=>app.quit());
app.on('before-quit',event=>{
  if(quitting || !backend)return;
  event.preventDefault();quitting=true;
  const child=backend.child;
  const stopped=new Promise(resolve=>{if(child.exitCode!==null)resolve();else child.once('exit',resolve);});
  void request('/api/shutdown',{}).catch(()=>{}).finally(()=>child.stdin.end());
  const timer=setTimeout(()=>{child.kill();app.exit(0);},20000);timer.unref();
  void stopped.then(()=>{clearTimeout(timer);app.exit(0);});
});
