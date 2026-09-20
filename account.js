'use strict';
// Session stays in memory; passwords and access codes never enter URLs or localStorage.
let session = '', currentOrder = null, account = null, config = null;
const $ = id => document.getElementById(id);
const money = cents => new Intl.NumberFormat('en-US', {style:'currency',currency:'USD'}).format(cents/100);
const statusNames = {awaiting_payment:'Awaiting payment',pending_review:'Pending review',approved:'Approved',rejected:'Rejected',cancelled:'Cancelled'};
function message(text) { $('message').textContent = text; }
async function api(path, data) {
  const headers = {};
  if (session) headers.Authorization = 'Bearer ' + session;
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  const result = await fetch(path, {method:data===undefined?'GET':'POST',headers,body:data===undefined?undefined:JSON.stringify(data),cache:'no-store',signal:AbortSignal.timeout(20000)});
  const value = await result.json();
  if (!result.ok) throw new Error(value.error?.message || 'Unable to complete this request. Try again.');
  return value;
}
function bind(id, action, submit=false) {
  $(id).addEventListener(submit?'submit':'click', async event => {
    event.preventDefault();
    const controls = submit ? [...$(id).querySelectorAll('button')] : [$(id)];
    controls.forEach(el=>el.disabled=true); message('');
    try { await action(); } catch (error) { message(error.name==='TimeoutError'?'Request timed out. Refresh status before trying again.':error.message); }
    finally { controls.forEach(el=>el.disabled=false); }
  });
}
const fields = id => Object.fromEntries(new FormData($(id)));
function el(tag,text,klass) { const node=document.createElement(tag); if(text)node.textContent=text;if(klass)node.className=klass;return node; }
function button(text, action) {
  const node=el('button',text);node.type='button';node.addEventListener('click',async()=>{
    node.disabled=true;message('');try{await action();}catch(error){message(error.message);}finally{node.disabled=false;}
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
  const result=await api('/v1/account/'+mode,fields(mode));session=result.access_token;$(mode).reset();await refresh();
},true);
bind('refresh',refresh);
bind('logout',async()=>{await api('/v1/account/logout',{});session='';location.reload();});
bind('copy',async()=>{await navigator.clipboard.writeText(session);message('Private code copied. Paste it only in your desktop app.');});
for(const plan of ['monthly','one_time'])bind(plan,async()=>{
  await api('/v1/payments/orders',{plan});await refresh();$('pay').scrollIntoView({block:'start'});
});
bind('report',async()=>{if(!currentOrder)throw new Error('Select a plan first.');await api('/v1/payments/orders/'+currentOrder.id+'/report',fields('report'));$('report').reset();await refresh();message('Payment reported. Wait for the administrator to verify it.');},true);
bind('owner',async()=>{await api('/v1/account/owner',fields('owner'));$('owner').reset();await refresh();},true);
bind('settings',async()=>{await api('/v1/admin/payments/settings',{...fields('settings'),enabled:$('settings').elements.enabled.checked});await refresh();message('Payment settings saved.');},true);
