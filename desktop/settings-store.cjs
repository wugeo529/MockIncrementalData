const fs = require('node:fs');
const path = require('node:path');

function allowedSender(url, origin) {
  try { const parsed=new URL(url); return parsed.origin===origin && parsed.pathname==='/' && !parsed.username && !parsed.password; }
  catch { return false; }
}

class SettingsStore {
  constructor(file, encryption) { this.file=file; this.encryption=encryption; }
  raw() {
    if(!fs.existsSync(this.file)) return {format:1,profiles:{}};
    const result=JSON.parse(fs.readFileSync(this.file,'utf8'));
    if(result.format!==1 || !result.profiles || typeof result.profiles!=='object') throw new Error('本机连接配置格式无法识别');
    return result;
  }
  load() {
    const result={};
    for(const [engine,value] of Object.entries(this.raw().profiles)) {
      if(!['mysql','postgresql'].includes(engine) || value.engine!==engine) continue;
      const config={engine,host:value.host,port:value.port,database:value.database,user:value.user,password:''};
      if(value.encryptedPassword && this.encryption.isEncryptionAvailable()) {
        try { config.password=this.encryption.decryptString(Buffer.from(value.encryptedPassword,'base64')); }
        catch { /* OS account/host changed: ask for password again, never use another fallback. */ }
      }
      result[engine]=config;
    }
    return result;
  }
  save(config, remember) {
    let encryptedPassword;
    if(remember && config.password) {
      if(!this.encryption.isEncryptionAvailable() || this.encryption.getSelectedStorageBackend?.()==='basic_text') throw new Error('本机安全密钥存储不可用，密码仅可用于本次会话');
      encryptedPassword=this.encryption.encryptString(config.password).toString('base64');
    }
    const value={engine:config.engine,host:config.host,port:config.port,database:config.database,user:config.user,...(encryptedPassword?{encryptedPassword}:{})};
    const stored=this.raw(); stored.profiles[config.engine]=value;
    fs.mkdirSync(path.dirname(this.file),{recursive:true});
    const temporary=this.file+'.tmp';
    fs.writeFileSync(temporary,JSON.stringify(stored,null,2),{encoding:'utf8',mode:0o600});
    fs.renameSync(temporary,this.file);
  }
}

module.exports={SettingsStore,allowedSender};
