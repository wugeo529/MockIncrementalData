const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { SettingsStore, allowedSender } = require('../desktop/settings-store.cjs');

const crypto = { isEncryptionAvailable: () => true,
  encryptString: value => Buffer.from('sealed:' + value),
  decryptString: bytes => bytes.toString().slice('sealed:'.length) };
const profile = {engine:'mysql',host:'127.0.0.1',port:3306,database:'signal_sim_demo',user:'root',password:'not-a-real-password'};

test('saved connection reloads through OS secret adapter and never persists plaintext password', t => {
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mock-source-settings-'));
  t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  const store=new SettingsStore(path.join(dir,'connections.json'),crypto);
  store.save(profile,true);
  const raw=fs.readFileSync(store.file,'utf8');
  assert.ok(!raw.includes(profile.password));
  assert.equal(JSON.parse(raw).profiles.mysql.password,undefined);
  assert.equal(store.load().mysql.password,profile.password);
});
test('no remember persists metadata with no password; unavailable encryption never falls back to plaintext', t => {
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mock-source-settings-'));
  t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  const store=new SettingsStore(path.join(dir,'connections.json'),crypto);
  store.save(profile,false);
  assert.equal(store.load().mysql.password,'');
  const denied=new SettingsStore(store.file,{isEncryptionAvailable:()=>false});
  assert.throws(()=>denied.save(profile,true),/安全|密码/);
  assert.equal(store.load().mysql.password,'');
});
test('only the local main renderer can configure desktop connections',()=>{
 const base='http://127.0.0.1:45678';
 assert.equal(allowedSender(base+'/',base),true);
 for(const url of ['http://127.0.0.1:45679/','https://example.com/','file:///x','http://127.0.0.1:45678/other','http://127.0.0.1:45678.evil.test/'])assert.equal(allowedSender(url,base),false,url);
});
