/* Real packaged desktop acceptance; credentials stay in a private input file. */
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const { _electron }=require(process.env.PLAYWRIGHT_MODULE || 'playwright');

async function run(){
  const [executable,configPath,reportDirectory]=process.argv.slice(2);
  if(!executable||!configPath||!reportDirectory)throw Error('Usage: node scripts/desktop_acceptance.cjs <exe> <private config> <report directory>');
  const config={...JSON.parse(fs.readFileSync(configPath,'utf8').replace(/^\uFEFF/,'')),database:'signal_sim_accept_'+crypto.randomBytes(8).toString('hex')};
  assert.equal(config.engine,'mysql');
  const python=process.env.PYTHON_EXE || 'python';
  const fixture=(drop=false)=>execFileSync(python,['-c',
    'import sys,json,pymysql; c=json.load(sys.stdin); db=c.pop("database"); c.pop("engine",None); assert db.startswith("signal_sim_accept_") and len(db)==34; conn=pymysql.connect(**c,autocommit=True); cur=conn.cursor(); cur.execute(("DROP DATABASE IF EXISTS `" if '+(drop?'True':'False')+' else "CREATE DATABASE `")+db+"`"); conn.close()'],{input:JSON.stringify(config),windowsHide:true,stdio:['pipe','pipe','pipe']});
  const results=[];let application,settings,previous,base;
  fs.mkdirSync(reportDirectory,{recursive:true});
  fixture();
  try{
    const launch=async()=>{
      application=await _electron.launch({executablePath:executable,env:{...process.env,PATH:process.env.SystemRoot+'\\System32'},timeout:45000});
      const page=await application.firstWindow();
      await page.locator('#configure').waitFor();
      await page.waitForFunction(()=>document.querySelector('#profile').options.length===2);
      return page;
    };
    let page=await launch();base=new URL(page.url()).origin;
    settings=path.join(await application.evaluate(({app})=>app.getPath('userData')),'connections.json');
    previous=fs.existsSync(settings)?fs.readFileSync(settings):null;
    assert.equal(await page.evaluate(()=>typeof require),'undefined');
    const preferences=await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences());
    assert.equal(preferences.sandbox,true);assert.equal(preferences.contextIsolation,true);assert.equal(preferences.nodeIntegration,false);
    await page.locator('#configure').click();
    for(const field of ['host','port','database','user','password'])await page.locator('#connection-'+field).fill(String(config[field]));
    await page.locator('#test-connection').click();
    await page.locator('#connection-message').filter({hasText:'连接成功'}).waitFor();
    await page.locator('#save-connection').click();
    await page.locator('#connection-message').filter({hasText:'连接已保存'}).waitFor();
    await page.locator('#initialize').click();await page.locator('#cancel-initialize').click();
    await page.locator('#initialize').click();await page.locator('#confirm-initialize').click();
    await page.locator('#connection-message').filter({hasText:'初始化完成'}).waitFor();
    // An unsaved target must never initialize the previously saved database.
    await page.locator('#connection-database').fill('signal_sim_unsaved');await page.locator('#initialize').click();
    await page.locator('#connection-message').filter({hasText:'请先保存'}).waitFor();
    await page.locator('#close-connection').click();
    await page.waitForFunction(()=>document.querySelector('#count-gps').textContent==='6');
    results.push('packaged startup without Python/Node PATH; renderer isolation; test/save/init/cancel; unsaved target guard');
    const count=async(n)=>{await page.waitForFunction(n=>document.querySelector('#count-gps').textContent===String(n),n);};
    await page.locator('[data-action=insert]').click();await count(7);
    await page.locator('[data-action=update]').click();await page.locator('#message').filter({hasText:'修改已提交'}).waitFor();
    await page.locator('[data-action=delete]').click();await page.locator('#cancel-delete').click();await count(7);
    await page.locator('[data-action=delete]').click();await page.locator('#confirm-delete').click();await count(6);
    for(const table of ['gps','ipsession','target']){await page.locator('[data-table='+table+']').click();assert.ok(await page.locator('#data tbody tr').count());}
    await page.locator('#interval').fill('0.2');await page.locator('#ticks').fill('3');await page.locator('#start').click();
    await page.locator('#progress').filter({hasText:'3 / 3'}).waitFor();await page.waitForFunction(()=>document.querySelector('#start').disabled===false);await count(8);
    await page.locator('#interval').fill('5');await page.locator('#ticks').fill('100');await page.locator('#start').click();
    await page.locator('#stop').click();await page.waitForFunction(()=>document.querySelector('#stop').disabled===true);
    await page.locator('#refresh').click();
    await page.screenshot({path:path.join(reportDirectory,'windows-desktop.png'),fullPage:true});
    const stored=fs.readFileSync(settings,'utf8');assert.ok(!config.password||!stored.includes(config.password));assert.ok(stored.includes('encryptedPassword'));
    results.push('real three-table INSERT/UPDATE/DELETE; delete cancel/confirm; all table tabs; bounded auto; active stop; refresh; OS-encrypted settings');
    await application.close();application=null;
    await assert.rejects(fetch(base+'/api/bootstrap'));
    page=await launch();base=new URL(page.url()).origin;
    await page.waitForFunction(()=>document.querySelector('#connection').textContent==='源库已连接');
    assert.ok((await page.locator('#endpoint').textContent()).includes(config.database));
    await application.close();application=null;
    await assert.rejects(fetch(base+'/api/bootstrap'));
    results.push('restart restores encrypted connection; backend stops after window exit twice');
    const report={passed:true,executable:path.basename(executable),date:new Date().toISOString(),checks:results};
    fs.writeFileSync(path.join(reportDirectory,'windows-desktop-results.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  }finally{
    if(application)await application.close().catch(()=>{});
    if(settings){if(previous)fs.writeFileSync(settings,previous);else if(fs.existsSync(settings))fs.unlinkSync(settings);}
    fixture(true);
  }
}
run().catch(error=>{console.error(error.stack);process.exitCode=1;});
