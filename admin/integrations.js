(()=>{
 const cfg=window.BB610_ADMIN_CONFIG||{},base=(cfg.apiBaseUrl||'').replace(/\/$/,''),ep='/api/v1/admin/integrations/nova-poshta',payEp='/api/v1/admin/integrations/payments',$=id=>document.getElementById(id),token=$('token');token.value=sessionStorage.getItem('bb610_admin_token')||'';
 const H=()=>({'Authorization':'Bearer '+token.value.trim(),'Content-Type':'application/json','Accept':'application/json'});
 async function req(path,opt={}){const c=new AbortController(),t=setTimeout(()=>c.abort(),cfg.requestTimeoutMs||12000);try{const r=await fetch(base+path,{...opt,signal:c.signal,headers:{...H(),...(opt.headers||{})}});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||`HTTP ${r.status}`);return d}finally{clearTimeout(t)}}
 const mark=(id,ok,yes='Готово',no='Не готово')=>{const e=$(id);e.textContent=ok?yes:no;e.className=ok?'ok':'warn'};
 function paint(s){
   mark('api-state',s.api_ready,'Доступний','Недоступний');mark('checkout-state',s.checkout_ready,'Готово','Не підключено');mark('cod-state',s.cod_ready,'Готово','Не активовано');mark('shipment-state',s.shipment_ready,'Готово','Не налаштовано');
   $('shipment-note').textContent=s.shipment_ready?'ТТН створюється з картки замовлення.':'Оберіть відправника, контакт, місто та відділення.';
   $('key-source').textContent=s.api_key?.configured?`Ключ: ${s.api_key.source==='secure_store'?'захищене сховище':'поточний .env'}`:'';
   $('api-url').value=s.api_url||'https://api.novaposhta.ua/v2.0/json/';$('np-status').textContent=s.configured?'Підключено':'Не підключено';$('np-status').className='badge '+(s.configured?'live':'draft');
   $('sender-select').dataset.current=s.sender?.sender_ref||'';$('contact-select').dataset.current=s.sender?.sender_contact_ref||'';$('sender-city-select').dataset.current=s.sender?.sender_city_ref||'';$('address-select').dataset.current=s.sender?.sender_address_ref||'';
   const sh=s.shipping||{};$('shipment-weight').value=sh.weight||'1.0';$('shipment-description').value=sh.description||'Товари для вирощування';$('payer-type').value=sh.payer_type||'Recipient';$('payment-method').value=sh.payment_method||'Cash';
 }
 async function load(){sessionStorage.setItem('bb610_admin_token',token.value.trim());$('state').textContent='Завантаження…';const [s,p]=await Promise.all([req(ep),req(payEp)]);paint(s);paintPayments(p);if(s.api_ready){try{await loadSenderOptions(true)}catch(_){}}$('state').textContent=''}
 function paintPayments(p){const cod=!!p.cod?.enabled,bank=!!p.bank_transfer?.ready,bankEnabled=!!p.bank_transfer?.enabled,card=!!p.online_card?.enabled;mark('pay-cod-state',cod,'Активна','Вимкнена');mark('pay-bank-state',bank,'Готова',bankEnabled?'Не завершено':'Вимкнена');$('pay-bank-note').textContent=bank?'Реквізити заповнені.':(bankEnabled?'Заповніть отримувача та IBAN.':'');mark('pay-card-state',card,card?(p.online_card?.provider||'Активна'):'Stage 14B','Stage 14B');$('pay-status').textContent=(cod||bank||card)?'Налаштовано':'Не налаштовано';$('pay-status').className='badge '+((cod||bank||card)?'live':'draft');$('pay-cod-enabled').checked=cod;$('pay-bank-enabled').checked=bankEnabled;$('pay-bank-recipient').value=p.bank_transfer?.recipient||'';$('pay-bank-iban').value=p.bank_transfer?.iban||'';$('pay-bank-purpose').value=p.bank_transfer?.purpose||'Оплата замовлення {order_number}'}
 async function savePayments(){const body={cod_enabled:$('pay-cod-enabled').checked,bank_transfer_enabled:$('pay-bank-enabled').checked,bank_recipient:$('pay-bank-recipient').value.trim(),bank_iban:$('pay-bank-iban').value.trim(),bank_purpose:$('pay-bank-purpose').value.trim()};$('pay-state').textContent='Збереження…';const p=await req(payEp,{method:'PATCH',body:JSON.stringify(body)});paintPayments(p);$('pay-state').textContent='✓ Збережено'}

 async function loadSenderOptions(silent=false){
   const b=$('load-senders');b.disabled=true;if(!silent)$('state').textContent='Завантаження відправників…';
   try{
     const d=await req(ep+'/senders'),cur=$('sender-select').dataset.current||'';
     $('sender-select').innerHTML='<option value="">Оберіть відправника</option>'+(d.senders||[]).map(x=>`<option value="${x.ref}" ${x.ref===cur?'selected':''}>${x.label||x.ref}${x.city?' · '+x.city:''}</option>`).join('');
     if(cur && !$('sender-select').value)$('sender-select').value=cur;
     if($('sender-select').value)await loadContacts($('sender-select').value);
     const cityCur=$('sender-city-select').dataset.current||'';
     if(cityCur){await restoreCity(cityCur);await loadBranches($('sender-select').value,cityCur);}
     if(!silent)$('state').textContent=`✓ Відправників: ${(d.senders||[]).length}`;
   }catch(e){if(!silent)$('state').textContent='✕ '+e.message;throw e}finally{b.disabled=false}
 }
 async function loadContacts(senderRef){
   $('contact-select').disabled=true;
   try{
     const d=await req(ep+'/sender-options?sender_ref='+encodeURIComponent(senderRef)),cc=$('contact-select').dataset.current||'';
     $('contact-select').innerHTML='<option value="">Оберіть контакт</option>'+(d.contacts||[]).map(x=>`<option value="${x.ref}" ${x.ref===cc?'selected':''}>${x.label||x.ref}${x.phone?' · '+x.phone:''}</option>`).join('');
     if(cc)$('contact-select').value=cc;
     if(!(d.contacts||[]).length)$('state').textContent='✕ Для цього відправника Nova Poshta не повернула контактних осіб';
   }finally{$('contact-select').disabled=false}
 }
 async function searchCities(){
   const q=$('sender-city-query').value.trim();if(q.length<2)throw new Error('Введіть щонайменше 2 символи назви міста');
   const b=$('search-sender-city');b.disabled=true;$('state').textContent='Пошук міста…';
   try{
     const d=await req(ep+'/cities?q='+encodeURIComponent(q)),cur=$('sender-city-select').dataset.current||'';
     $('sender-city-select').innerHTML='<option value="">Оберіть місто</option>'+(d.cities||[]).map(x=>`<option value="${x.ref}" ${x.ref===cur?'selected':''}>${x.name||x.ref}${x.region?' · '+x.region:''}</option>`).join('');
     $('sender-city-select').disabled=false;$('state').textContent=`✓ Міст: ${(d.cities||[]).length}`;
   }finally{b.disabled=false}
 }
 async function restoreCity(cityRef){
   try{
     const d=await req(ep+'/cities?city_ref='+encodeURIComponent(cityRef)),x=(d.cities||[])[0];
     $('sender-city-select').innerHTML=x?`<option value="${x.ref}" selected>${x.name||x.ref}${x.region?' · '+x.region:''}</option>`:`<option value="${cityRef}" selected>Збережене місто</option>`;
     $('sender-city-select').disabled=false;
   }catch(_){$('sender-city-select').innerHTML=`<option value="${cityRef}" selected>Збережене місто</option>`;$('sender-city-select').disabled=false}
 }
 async function loadBranches(senderRef,cityRef){
   $('address-select').disabled=true;
   try{
     const d=await req(ep+'/sender-options?sender_ref='+encodeURIComponent(senderRef)+'&city_ref='+encodeURIComponent(cityRef)),ac=$('address-select').dataset.current||'';
     $('address-select').innerHTML='<option value="">Оберіть відділення / точку відправлення</option>'+(d.addresses||[]).map(x=>`<option value="${x.ref}" ${x.ref===ac?'selected':''}>${x.label||x.ref}</option>`).join('');
     if(ac)$('address-select').value=ac;
     if(!(d.addresses||[]).length)$('state').textContent='✕ У вибраному місті не знайдено доступних відділень Nova Poshta';
   }catch(e){$('address-select').innerHTML='<option value="">Не вдалося завантажити відділення</option>';$('state').textContent='✕ '+e.message;throw e}
   finally{$('address-select').disabled=false}
 }
 async function save(){
   const sr=$('sender-select').value.trim(),cr=$('contact-select').value.trim(),city=$('sender-city-select').value.trim(),ar=$('address-select').value.trim();
   if((sr||cr||city||ar)&&!(sr&&cr&&city&&ar))throw new Error('Оберіть відправника, контактну особу, місто та відділення відправлення');
   const body={api_url:$('api-url').value.trim(),sender_ref:sr,sender_contact_ref:cr,sender_city_ref:city,sender_address_ref:ar,shipment_weight:Number($('shipment-weight').value||1),shipment_description:$('shipment-description').value.trim(),payer_type:$('payer-type').value,payment_method:$('payment-method').value};
   const k=$('api-key').value.trim();if(k)body.api_key=k;$('state').textContent='Збереження…';const s=await req(ep,{method:'PATCH',body:JSON.stringify(body)});$('api-key').value='';
   if(sr&&(!s.sender||s.sender.sender_ref!==sr||s.sender.sender_contact_ref!==cr||s.sender.sender_city_ref!==city||s.sender.sender_address_ref!==ar))throw new Error('Налаштування відправника не збережені повністю.');
   paint(s);if(s.sender?.sender_ref)await loadSenderOptions(true);$('state').textContent=s.sender_ready?'✓ Відправник, контакт, місто та відділення збережені':'✓ Налаштування збережено';
 }
 async function test(){const b=$('test');b.disabled=true;$('state').textContent='Перевірка Nova Poshta…';try{const r=await req(ep+'/test',{method:'POST',body:'{}'});$('state').textContent=`✓ API працює · знайдено ${r.results} результатів`;await load()}catch(e){$('state').textContent='✕ '+e.message}finally{b.disabled=false}}
 $('connect').onclick=()=>load().catch(e=>$('state').textContent='✕ '+e.message);$('pay-save').onclick=()=>savePayments().catch(e=>$('pay-state').textContent='✕ '+e.message);$('save').onclick=()=>save().catch(e=>$('state').textContent='✕ '+e.message);$('test').onclick=test;$('load-senders').onclick=()=>loadSenderOptions(false);
 $('sender-select').onchange=()=>{$('sender-select').dataset.current=$('sender-select').value;$('contact-select').dataset.current='';$('sender-city-select').dataset.current='';$('address-select').dataset.current='';$('sender-city-select').innerHTML='<option value="">Спочатку знайдіть місто</option>';$('address-select').innerHTML='<option value="">Спочатку оберіть місто</option>';if($('sender-select').value)loadContacts($('sender-select').value).catch(e=>$('state').textContent='✕ '+e.message)};
 $('contact-select').onchange=()=>{$('contact-select').dataset.current=$('contact-select').value};$('search-sender-city').onclick=()=>searchCities().catch(e=>$('state').textContent='✕ '+e.message);
 $('sender-city-select').onchange=()=>{const v=$('sender-city-select').value;$('sender-city-select').dataset.current=v;$('address-select').dataset.current='';if(v&&$('sender-select').value)loadBranches($('sender-select').value,v).catch(()=>{})};
 $('address-select').onchange=()=>{$('address-select').dataset.current=$('address-select').value};$('toggle-key').onclick=()=>{const x=$('api-key');x.type=x.type==='password'?'text':'password'};if(token.value)load().catch(e=>$('state').textContent='✕ '+e.message)
})();
