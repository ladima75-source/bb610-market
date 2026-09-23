(()=>{
 const cfg=window.BB610_ADMIN_CONFIG||{},base=(cfg.apiBaseUrl||'').replace(/\/$/,''),ep='/api/v1/admin/integrations/nova-poshta',payEp='/api/v1/admin/integrations/payments',tgEp='/api/v1/admin/integrations/telegram',cbEp='/api/v1/admin/integrations/checkbox',metaEp='/api/v1/admin/integrations/meta-capi',$=id=>document.getElementById(id),token=$('token');token.value=localStorage.getItem('bb610_admin_token')||sessionStorage.getItem('bb610_admin_token')||'';
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
 async function load(){localStorage.setItem('bb610_admin_token',token.value.trim());sessionStorage.setItem('bb610_admin_token',token.value.trim());$('state').textContent='Завантаження…';const [s,p,tg,cb,meta]=await Promise.all([req(ep),req(payEp),req(tgEp),req(cbEp),req(metaEp)]);paint(s);paintPayments(p);paintTelegram(tg);paintCheckbox(cb);paintMeta(meta);if(s.api_ready){try{await loadSenderOptions(true)}catch(_){}}$('state').textContent=''}
 function paintPayments(p){const cod=!!p.cod?.enabled,bank=!!p.bank_transfer?.ready,bankEnabled=!!p.bank_transfer?.enabled,card=!!p.online_card?.enabled;mark('pay-cod-state',cod,'Активна','Вимкнена');mark('pay-bank-state',bank,'Готова',bankEnabled?'Не завершено':'Вимкнена');$('pay-bank-note').textContent=bank?'Реквізити заповнені.':(bankEnabled?'Заповніть отримувача та IBAN.':'');mark('pay-card-state',card,card?'mono':'Не підключено','Не підключено');$('pay-card-note').textContent=card?'Token збережено · webhook готовий':'mono Еквайринг';$('pay-mono-webhook').value=p.online_card?.webhook_url||'https://api.market.bb610.com.ua/api/v1/payments/webhooks/mono';$('pay-status').textContent=(cod||bank||card)?'Налаштовано':'Не налаштовано';$('pay-status').className='badge '+((cod||bank||card)?'live':'draft');$('pay-cod-enabled').checked=cod;$('pay-bank-enabled').checked=bankEnabled;$('pay-bank-recipient').value=p.bank_transfer?.recipient||'';$('pay-bank-iban').value=p.bank_transfer?.iban||'';$('pay-bank-purpose').value=p.bank_transfer?.purpose||'Оплата замовлення {order_number}'}
 async function savePayments(){const body={cod_enabled:$('pay-cod-enabled').checked,bank_transfer_enabled:$('pay-bank-enabled').checked,bank_recipient:$('pay-bank-recipient').value.trim(),bank_iban:$('pay-bank-iban').value.trim(),bank_purpose:$('pay-bank-purpose').value.trim()};const mt=$('pay-mono-token').value.trim();if(mt)body.mono_token=mt;$('pay-state').textContent='Збереження…';const p=await req(payEp,{method:'PATCH',body:JSON.stringify(body)});$('pay-mono-token').value='';paintPayments(p);$('pay-state').textContent='✓ Збережено'}
 async function testMono(){const b=$('pay-mono-test');b.disabled=true;$('pay-state').textContent='Перевірка mono…';try{await req(payEp+'/mono/test',{method:'POST',body:'{}'});$('pay-state').textContent='✓ mono API доступний';await load()}catch(e){$('pay-state').textContent='✕ '+e.message}finally{b.disabled=false}}

 function paintMeta(m){const ready=!!m.configured;mark('meta-token-state',ready,'Збережено','Не налаштовано');$('meta-token-source').textContent=ready?`Token: ${m.access_token?.source==='secure_store'?'захищене сховище':'поточний .env'}`:'';$('meta-pixel-state').textContent=m.pixel_id||'1103668908981910';$('meta-dedupe-state').textContent=m.deduplication||'event_id';$('meta-status').textContent=ready?'Підключено':'Не підключено';$('meta-status').className='badge '+(ready?'live':'draft')}
 async function saveMeta(){const t=$('meta-access-token').value.trim();if(!t)throw new Error('Вставте Access Token Meta');$('meta-state').textContent='Збереження…';const m=await req(metaEp,{method:'PATCH',body:JSON.stringify({access_token:t})});$('meta-access-token').value='';paintMeta(m);$('meta-state').textContent='✓ Meta CAPI token збережено'}
 function paintCheckbox(c){const login=!!c.cashier_login?.configured,ready=!!c.configured;mark('cb-login-state',login,'Збережено','Не налаштовано');mark('cb-api-state',ready,'Готовий','Не підключено');mark('cb-auto-state',ready,'Готово до активації','Очікує підключення');$('cb-status').textContent=ready?'Налаштовано':'Не підключено';$('cb-status').className='badge '+(ready?'live':'draft');$('cb-login').value=''}
 async function saveCheckbox(){const body={};const l=$('cb-login').value.trim(),p=$('cb-password').value;if(l)body.cashier_login=l;if(p)body.cashier_password=p;if(!Object.keys(body).length)throw new Error('Введіть логін і пароль касира Checkbox');$('cb-state').textContent='Збереження…';const c=await req(cbEp,{method:'PATCH',body:JSON.stringify(body)});$('cb-login').value='';$('cb-password').value='';paintCheckbox(c);$('cb-state').textContent='✓ Доступ збережено'}
 async function testCheckbox(){const b=$('cb-test');b.disabled=true;$('cb-state').textContent='Перевірка Checkbox…';try{await req(cbEp+'/test',{method:'POST',body:'{}'});$('cb-state').textContent='✓ Checkbox API доступний';await load()}catch(e){$('cb-state').textContent='✕ '+e.message}finally{b.disabled=false}}
 function paintTelegram(t){
   const tokenReady=!!t.bot_token?.configured,chatReady=!!t.chat_id?.configured,ready=!!t.price_request_notifications_ready;
   mark('tg-token-state',tokenReady,'Збережено','Не налаштовано');
   mark('tg-chat-state',chatReady,'Збережено','Не налаштовано');
   mark('tg-ready-state',ready,'Готово','Не готово');
   $('tg-token-source').textContent=tokenReady?`Token: ${t.bot_token?.source==='secure_store'?'захищене сховище':'поточний .env'}`:'';
   $('tg-chat-id').value=t.chat_id?.value||'';
   $('tg-status').textContent=ready?'Підключено':'Не підключено';
   $('tg-status').className='badge '+(ready?'live':'draft');
 }
 async function saveTelegram(){
   const body={chat_id:$('tg-chat-id').value.trim()};
   const k=$('tg-bot-token').value.trim();if(k)body.bot_token=k;
   $('tg-state').textContent='Збереження…';
   const t=await req(tgEp,{method:'PATCH',body:JSON.stringify(body)});
   $('tg-bot-token').value='';paintTelegram(t);
   $('tg-state').textContent=t.price_request_notifications_ready?'✓ Telegram збережено':'✓ Налаштування збережено. Додайте Bot token.';
 }
 async function testTelegram(){
   const b=$('tg-test');b.disabled=true;$('tg-state').textContent='Надсилаємо тест…';
   try{const r=await req(tgEp+'/test',{method:'POST',body:'{}'});$('tg-state').textContent='✓ Тестове повідомлення надіслано · message '+(r.message_id||'');await load()}
   catch(e){$('tg-state').textContent='✕ '+e.message}
   finally{b.disabled=false}
 }

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
 $('meta-save').onclick=()=>saveMeta().catch(e=>$('meta-state').textContent='✕ '+e.message);$('meta-toggle-token').onclick=()=>{const x=$('meta-access-token');x.type=x.type==='password'?'text':'password'};$('cb-save').onclick=()=>saveCheckbox().catch(e=>$('cb-state').textContent='✕ '+e.message);$('cb-test').onclick=testCheckbox;$('cb-toggle-password').onclick=()=>{const x=$('cb-password');x.type=x.type==='password'?'text':'password'};$('connect').onclick=()=>load().catch(e=>$('state').textContent='✕ '+e.message);$('pay-save').onclick=()=>savePayments().catch(e=>$('pay-state').textContent='✕ '+e.message);$('pay-mono-test').onclick=testMono;$('pay-toggle-mono').onclick=()=>{const x=$('pay-mono-token');x.type=x.type==='password'?'text':'password'};$('tg-save').onclick=()=>saveTelegram().catch(e=>$('tg-state').textContent='✕ '+e.message);$('tg-test').onclick=testTelegram;$('save').onclick=()=>save().catch(e=>$('state').textContent='✕ '+e.message);$('test').onclick=test;$('load-senders').onclick=()=>loadSenderOptions(false);
 $('sender-select').onchange=()=>{$('sender-select').dataset.current=$('sender-select').value;$('contact-select').dataset.current='';$('sender-city-select').dataset.current='';$('address-select').dataset.current='';$('sender-city-select').innerHTML='<option value="">Спочатку знайдіть місто</option>';$('address-select').innerHTML='<option value="">Спочатку оберіть місто</option>';if($('sender-select').value)loadContacts($('sender-select').value).catch(e=>$('state').textContent='✕ '+e.message)};
 $('contact-select').onchange=()=>{$('contact-select').dataset.current=$('contact-select').value};$('search-sender-city').onclick=()=>searchCities().catch(e=>$('state').textContent='✕ '+e.message);
 $('sender-city-select').onchange=()=>{const v=$('sender-city-select').value;$('sender-city-select').dataset.current=v;$('address-select').dataset.current='';if(v&&$('sender-select').value)loadBranches($('sender-select').value,v).catch(()=>{})};
 $('address-select').onchange=()=>{$('address-select').dataset.current=$('address-select').value};$('toggle-key').onclick=()=>{const x=$('api-key');x.type=x.type==='password'?'text':'password'};$('tg-toggle-token').onclick=()=>{const x=$('tg-bot-token');x.type=x.type==='password'?'text':'password'};if(token.value)load().catch(e=>$('state').textContent='✕ '+e.message)
})();
