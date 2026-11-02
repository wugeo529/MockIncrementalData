const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
test('slow dashboard polling stays single-flight and refreshes the queued latest profile',async()=>{
  const elements=new Map();const element=()=>({textContent:'',value:'mysql',disabled:false,dataset:{},classList:{toggle(){}},append(){},replaceChildren(){},querySelector(){return element();}});
  const pending=[];
  const context=vm.createContext({console,Date,encodeURIComponent,setInterval(){},document:{getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);},querySelectorAll(){return [];},createElement:element},fetch(url){if(url==='/api/bootstrap')return Promise.resolve({json:async()=>({token:'test',profiles:['mysql']})});return new Promise(resolve=>pending.push({url,resolve}));}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../engine/dashboard.js'),'utf8'),context);
  const state={connected:true,engine:'mysql',tables:{},runtime:{running:false,events:[]}};
  const finish=item=>item.resolve({ok:true,json:async()=>state});
  await new Promise(setImmediate);assert.equal(pending.length,1);finish(pending[0]);await new Promise(setImmediate);
  context.refresh();context.refresh();elements.get('profile').value='postgresql';context.refresh();
  assert.equal(pending.length,2,'do not overlap requests while a previous poll is slow');
  finish(pending[1]);await new Promise(setImmediate);assert.equal(pending.length,3);assert.ok(pending[2].url.endsWith('postgresql'));
  finish(pending[2]);await new Promise(setImmediate);
});
