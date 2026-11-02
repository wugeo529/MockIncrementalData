'use strict';

function connectionFields() {
  return {engine:$('connection-engine').value,host:$('connection-host').value.trim(),
    port:Number($('connection-port').value),database:$('connection-database').value.trim(),
    user:$('connection-user').value.trim(),password:$('connection-password').value,
    reusePassword:!$('connection-password').value};
}

function endpoint() {
  const value=connections[$('profile').value];
  setText('endpoint',value?`${value.host}:${value.port} / ${value.database}`:'首次使用请点击“数据库连接”。');
}

function showConnection(engine=$('profile').value || 'mysql') {
  const value=connections[engine]||{host:'127.0.0.1',port:engine==='mysql'?3306:5432,database:'signal_sim_demo',user:engine==='mysql'?'root':'postgres'};
  $('connection-engine').value=engine;
  for(const field of ['host','port','database','user'])$('connection-'+field).value=value[field];
  $('connection-password').value='';
  $('connection-password').placeholder=value.hasPassword?'已保存，留空沿用同一连接的密码':'请输入数据库密码';
  $('connection-message').textContent='';
  $('initialize-confirm').hidden=true;$('connection-dialog').hidden=false;
  $('remember-password').disabled=!window.mockDesktop;
}

async function connectionRequest(route,body) {
  const response=await fetch(route,{method:'POST',headers:{'Content-Type':'application/json','X-Simulator-Token':token},body:JSON.stringify(body)});
  const data=await response.json();if(!response.ok)throw Error(data.error||'操作未完成');return data;
}

async function connectionAction(name) {
  if(busy)return;
  busy=true;buttons();
  document.querySelectorAll('#connection-form button,#connection-engine').forEach(button=>button.disabled=true);
  $('connection-message').textContent='正在处理…';
  try {
    let data;const config=connectionFields();
    if(name==='test') data=await connectionRequest('/api/connection/test',config);
    else if(name==='save') data=window.mockDesktop
      ? await window.mockDesktop.saveConnection({...config,rememberPassword:$('remember-password').checked})
      : await connectionRequest('/api/connection/save',config);
    else data=await connectionRequest('/api/initialize',{profile:$('profile').value});
    if(name==='save') {
      connections[config.engine]=data.config;$('profile').value=config.engine;
      $('connection-password').value='';
      $('connection-password').placeholder=data.config.hasPassword?'已保存，留空沿用同一连接的密码':'';
    }
    const text=name==='test'
      ? data.schemaReady?'连接成功，三表结构可用。':data.databaseExists?'连接成功；三表尚未就绪，请先保存连接再初始化。':'连接成功；数据库尚未创建，请先保存连接再初始化。'
      : name==='save'?'连接已保存。'+(data.schemaReady?'可以开始模拟。':'首次使用请初始化模拟表。')
      : data.created?'三表初始化完成，已写入六组样例。':'已有三表校验通过，原数据已保留。';
    $('connection-message').textContent=data.warning||text;
    message('');endpoint();await refresh();
  } catch(error) { $('connection-message').textContent=error.message; }
  finally {
    busy=false;document.querySelectorAll('#connection-form button,#connection-engine').forEach(button=>button.disabled=false);buttons();
  }
}

$('configure').onclick=()=>showConnection();
$('connection-engine').onchange=()=>showConnection($('connection-engine').value);
$('close-connection').onclick=()=>{if(!busy){$('connection-password').value='';$('connection-dialog').hidden=true;}};
$('connection-form').onsubmit=event=>{event.preventDefault();connectionAction('save');};
$('test-connection').onclick=()=>connectionAction('test');
$('initialize').onclick=()=>{
  const candidate=connectionFields(), saved=connections[candidate.engine];
  if(candidate.engine!==$('profile').value || !saved || ['host','port','database','user'].some(key=>candidate[key]!==saved[key]) || candidate.password){$('connection-message').textContent='请先保存当前连接，再初始化。';return;}
  $('initialize-confirm').hidden=false;
};
$('cancel-initialize').onclick=()=>($('initialize-confirm').hidden=true);
$('confirm-initialize').onclick=()=>{$('initialize-confirm').hidden=true;connectionAction('initialize');};
$('profile').addEventListener('change',endpoint);
void fetch('/api/bootstrap').then(response=>response.json()).then(data=>{connections=data.connections||{};$('configure').hidden=!data.desktop;endpoint();}).catch(()=>{});
