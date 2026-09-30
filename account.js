'use strict';
// Session stays in memory; passwords and access codes never enter URLs or localStorage.
let session = '', currentOrder = null, account = null, config = null;
let busy = false;
const $ = id => document.getElementById(id);
const money = cents => new Intl.NumberFormat('en-US', {style:'currency',currency:'USD'}).format(cents/100);
const statusNames = {awaiting_payment:'Awaiting payment',pending_review:'Pending review',approved:'Approved',rejected:'Rejected',cancelled:'Cancelled'};
function message(text) { $('message').textContent = text; }
function clearSession() {
  session='';currentOrder=null;account=null;config=null;
  for(const id of ['member','admin','logout','pay','activation'])$(id).hidden=true;
  for(const id of ['history','queue','users'])$(id).replaceChildren();
  $('auth').hidden=false;
  $('server').value='';
  $('welcome').textContent='';$('access').textContent='';
  for(const id of ['destination','orderDetail','trialStatus'])$(id).textContent='';
  $('qr').removeAttribute('src');$('paymentLink').removeAttribute('href');
  $('trialCard').hidden=true;$('purchase').hidden=true;
  for(const id of ['login','register','owner','report','settings'])$(id).reset();
}
function errorMessage(error) {
  if(error.name==='TimeoutError' || error.name==='AbortError')return 'Request timed out. Refresh status before trying again.';
  if(error instanceof TypeError)return 'Connection lost. Check your Internet connection, then refresh status before repeating an action.';
  return error.message || 'Unable to complete this request. Try again.';
}
async function api(path, data) {
  const headers = {};
  if (session) headers.Authorization = 'Bearer ' + session;
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  const result = await fetch(path, {method:data===undefined?'GET':'POST',headers,body:data===undefined?undefined:JSON.stringify(data),cache:'no-store',signal:AbortSignal.timeout(20000)});
  if(session && (result.status===401 || result.status===403 && path==='/v1/account/me')) {
    clearSession();
    throw new Error('Your session expired or access was revoked. Sign in again to continue.');
  }
  let value;
  try { value = await result.json(); }
  catch { throw new Error('The server returned an unreadable response. Refresh status before trying again.'); }
  if(!value || typeof value!=='object' || Array.isArray(value))throw new Error('The server returned an invalid response. Try again later.');
  if (!result.ok) throw new Error(value.error?.message || 'Unable to complete this request. Try again.');
  return value;
}
async function runAction(action) {
  if(busy)return;
  busy=true;
  const controls=[...document.querySelectorAll('button')].map(node=>[node,node.disabled]);
  controls.forEach(([node])=>node.disabled=true);
  $('message').setAttribute('aria-busy','true');message('Working…');
  try { await action(); if($('message').textContent==='Working…')message(''); }
  catch(error) { message(errorMessage(error)); }
  finally {
    busy=false;
    controls.forEach(([node,disabled])=>node.disabled=disabled);
    $('monthly').disabled=$('one_time').disabled=!config?.enabled;
    $('message').removeAttribute('aria-busy');
  }
}
function bind(id, action, submit=false) {
  $(id).addEventListener(submit?'submit':'click', async event => {
    event.preventDefault();
    await runAction(action);
  });
}
const fields = id => Object.fromEntries(new FormData($(id)));
function el(tag,text,klass) { const node=document.createElement(tag); if(text)node.textContent=text;if(klass)node.className=klass;return node; }
function button(text, action) {
  const node=el('button',text);node.type='button';node.addEventListener('click',async()=>{
    await runAction(action);
  });return node;
}
function showOrder(order) {
  currentOrder=order; $('pay').hidden=!order || order.status!=='awaiting_payment';
  if($('pay').hidden)return;
  $('destination').textContent='Pay '+order.recipient+' · '+money(order.amount_cents)+' USD';
  $('paymentLink').href='https://cash.app/'+order.recipient;
  $('orderDetail').textContent='Purchase reference: '+order.id+'. Include this reference in your payment note.';
  $('qr').hidden=order.recipient!==config.cashtag || !config.enabled;
  if(!$('qr').hidden)$('qr').src='/v1/payments/qr.svg?v='+Date.now();
}
async function refresh() {
  account=(await api('/v1/account/me')).account;
  config=await api('/v1/payments/config');
  $('auth').hidden=true;$('member').hidden=false;$('logout').hidden=false;
  $('welcome').textContent='Hello, '+account.display_name;
  $('access').textContent=account.active ? (account.paid_until ? 'Access active through '+new Date(account.paid_until*1000).toLocaleDateString() : 'Your access is active.') : 'Access pending. You can wait for free approval or choose a paid plan.';
  $('activation').hidden=!account.active; $('server').value=location.origin;
  const permanent=['manual','paid_lifetime'].includes(account.access_reason);
  const trial=account.trial;
  $('trialCard').hidden=permanent || account.access_reason==='paid' && account.active;
  $('startTrial').hidden=!!trial;
  $('trialProgress').hidden=!trial;
  if(!trial)$('trialStatus').textContent='20 AI analyses over 48 hours, once per account. Corrections and retries count as analyses. No automatic charges.';
  if(trial){
    $('trialProgress').value=trial.remaining;
    const valid=trial.expires_at*1000>Date.now() && trial.remaining>0;
    $('trialStatus').textContent=valid ? `${trial.remaining} of ${trial.request_limit} analyses left · Ends ${new Date(trial.expires_at*1000).toLocaleString()}. No automatic charges.` : 'Your trial has ended. Choose a plan to continue; nothing has been charged.';
    if(account.access_reason==='trial')$('access').textContent=valid?'Free trial active. Download the app and sign in with this account.':'Free trial ended. Choose a plan to continue.';
  }
  $('purchase').hidden=permanent;
  $('disabled').textContent=config.enabled?'Payment is reviewed by the administrator before access is activated.':'Payments are not available yet. Please wait for the administrator.';
  $('monthly').disabled=$('one_time').disabled=!config.enabled;
  const orders=(await api('/v1/payments/orders')).orders;
  $('history').replaceChildren();
  for(const order of orders){
    const row=el('div',null,'row');row.append(el('p',money(order.amount_cents)+' · '+(order.plan==='monthly'?'One month':'Lifetime of service')),el('p',statusNames[order.status]||order.status,'pill'));
    if(order.review_note)row.append(el('p',order.review_note));
    if(order.status==='awaiting_payment')row.append(button('Cancel unpaid request',async()=>{await api('/v1/payments/orders/'+order.id+'/cancel',{});await refresh();}));
    $('history').append(row);
  }
  if(!orders.length)$('history').append(el('p','No payment requests yet.'));
  showOrder(orders.find(o=>o.status==='awaiting_payment')||null);
  $('admin').hidden=account.role!=='admin';
  if(account.role==='admin')await refreshAdmin();
}
async function refreshAdmin(){
  $('settings').elements.cashtag.value=config.cashtag;
  $('settings').elements.recipient_name.value=config.recipient_name;
  $('settings').elements.enabled.checked=config.enabled;
  const orders=(await api('/v1/admin/payments')).orders;
  $('queue').replaceChildren();
  for(const order of orders.filter(o=>o.status==='pending_review')){
    const row=el('form',null,'row');
    row.append(el('h3',order.display_name+' · '+money(order.amount_cents)),el('p',order.email),el('p','Recipient: '+order.recipient+' | Sender: '+order.payer),el('p','Reported reference: '+order.reported_reference));
    function input(label,name,type='text'){const l=el('label',label),i=el('input');i.name=name;i.type=type;i.maxLength=120;l.append(i);row.append(l);return i;}
    const reference=input('Verified transaction ID from your Cash App account','reference');
    const amount=input('Gross amount received in USD (before fees)','amount');amount.inputMode='decimal';
    const note=input('Review note (required for rejection)','note');note.maxLength=500;
    const confirmed=input('I checked that this payment completed in my Cash App account','confirmed','checkbox');confirmed.parentElement.className='check';
    row.append(button('Approve verified payment',async()=>{
      if(!confirmed.checked)throw new Error('Verify the completed payment in Cash App first.');
      if(!/^\d{1,5}(\.\d{1,2})?$/.test(amount.value))throw new Error('Enter the gross amount in USD, for example 10.00.');
      await api('/v1/admin/payments/'+order.id+'/review',{action:'approve',reference:reference.value,received_cents:Math.round(Number(amount.value)*100),note:note.value});
      await refresh();message('Payment approved. Access updated.');
    }),button('Reject request',async()=>{await api('/v1/admin/payments/'+order.id+'/review',{action:'reject',note:note.value});await refresh();message('Request rejected. No access granted.');}));
    row.addEventListener('submit',event=>event.preventDefault());$('queue').append(row);
  }
  if(!$('queue').children.length)$('queue').append(el('p','No payments awaiting review.'));
  $('users').replaceChildren();
  const users=(await api('/v1/admin/accounts')).accounts;
  for(const user of users){
    const row=el('div',null,'row');row.append(el('p',user.display_name+' · '+user.email),el('p',user.status+' · '+user.requests+'/'+user.daily_limit+' requests today'));
    if(user.id!==account.id)row.append(button('Approve free access',async()=>{if(!confirm('Give free ongoing access to '+user.email+'?'))return;await api('/v1/admin/accounts/'+user.id,{action:'approve'});await refresh();}),button('Block access',async()=>{if(!confirm('Block '+user.email+' and revoke their sessions?'))return;await api('/v1/admin/accounts/'+user.id,{action:'block'});await refresh();}));
    $('users').append(row);
  }
}
for(const mode of ['login','register'])bind(mode,async()=>{
  const result=await api('/v1/account/'+mode,fields(mode));
  if(typeof result.access_token!=='string' || !/^spc_[A-Za-z0-9_-]{40,100}$/.test(result.access_token))throw new Error('The server did not provide a valid session. Sign in again.');
  session=result.access_token;$(mode).reset();
  $('auth').hidden=true;$('member').hidden=false;$('logout').hidden=false;
  await refresh();
},true);
bind('refresh',refresh);
bind('startTrial',async()=>{await api('/v1/account/trial',{});await refresh();message('Trial activated. Download the app, open Mi cuenta and sign in.');});
bind('logout',async()=>{
  try { await api('/v1/account/logout',{});clearSession();message('Signed out.'); }
  catch(error) { clearSession();message('Signed out on this page. Server revocation could not be confirmed; close the page and sign in again when connected.'); }
});
bind('copy',async()=>{await navigator.clipboard.writeText(session);message('Private code copied. Paste it only in your desktop app.');});
for(const plan of ['monthly','one_time'])bind(plan,async()=>{
  await api('/v1/payments/orders',{plan});await refresh();$('pay').scrollIntoView({block:'start'});
});
bind('report',async()=>{if(!currentOrder)throw new Error('Select a plan first.');await api('/v1/payments/orders/'+currentOrder.id+'/report',fields('report'));$('report').reset();await refresh();message('Payment reported. Wait for the administrator to verify it.');},true);
bind('owner',async()=>{await api('/v1/account/owner',fields('owner'));$('owner').reset();await refresh();},true);
bind('settings',async()=>{await api('/v1/admin/payments/settings',{...fields('settings'),enabled:$('settings').elements.enabled.checked});await refresh();message('Payment settings saved.');},true);
