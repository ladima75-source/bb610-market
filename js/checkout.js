document.addEventListener('DOMContentLoaded',()=>{
  const root=document.getElementById('checkout-app');
  if(!root)return;
  const cart=BB610.get(BB610.LS.cart,[]).map(row=>({row,sku:BB610.sku(row.sku)})).filter(x=>x.sku).map(x=>({...x,p:BB610.byId(x.sku.product_id)}));
  const orderable=x=>x.sku.commercial_status==='active'&&x.sku.offer_status==='active'&&x.sku.price!==null&&x.sku.price!==undefined&&x.sku.availability!=='unknown'&&x.sku.availability!=='out_of_stock';
  const allOrderable=cart.length>0&&cart.every(orderable);
  const total=cart.reduce((s,x)=>s+(x.sku.price==null?0:Number(x.sku.price)*x.row.qty),0);
  const configured=BB610OrderClient.configured();
  if(cart.length)BB610.pushEvent('begin_checkout',{ecommerce:{currency:'UAH',value:cart.every(x=>x.sku.price!=null)?total:undefined,items:cart.map(x=>BB610.commerceItem(x.sku,x.row.qty))}});

  root.innerHTML=`<div class="checkout-layout">
    <form id="checkout-form" class="checkout-form" novalidate>
      <div class="info-card checkout-card"><div class="eyebrow">КОНТАКТНІ ДАНІ</div><h2>Оформлення без реєстрації</h2>
        <div class="field-grid"><label><span>Ім’я *</span><input name="name" autocomplete="name" required></label><label><span>Телефон *</span><input name="phone" inputmode="tel" autocomplete="tel" placeholder="+380..." required></label></div>
        <label><span>Email</span><input name="email" type="email" autocomplete="email" placeholder="Необов’язково"></label>
      </div>
      <div class="info-card checkout-card"><div class="eyebrow">ОТРИМАННЯ</div><h2>Спосіб отримання</h2>
        <label><span>Спосіб *</span><select name="method" required><option value="pickup_dnipro">Самовивіз у Дніпрі</option><option value="delivery_dnipro">Доставка по Дніпру</option><option value="shipping_ukraine">Відправка по Україні</option></select></label>
        <label><span>Місто / відділення / адреса</span><input name="destination" autocomplete="street-address" placeholder="Уточнюється залежно від способу"></label>
        <label><span>Коментар</span><textarea name="comment" rows="3" placeholder="Необов’язково"></textarea></label>
      </div>
      <div class="checkout-system-note ${configured&&allOrderable?'ready':'blocked'}">
        ${!configured?'<b>Backend замовлень ще не підключений.</b><span>Форма та API-контракт готові, але реальний заказ зараз не відправляється.</span>':!allOrderable?'<b>Не всі SKU готові до продажу.</b><span>Для оформлення потрібні активні SKU, підтверджені ціни та наявність.</span>':'<b>Замовлення готове до відправки.</b><span>Перед створенням замовлення backend повторно перевірить ціну та наявність.</span>'}
      </div>
      <button id="submit-order" class="btn checkout-submit" type="submit" ${configured&&allOrderable?'':'disabled'}>ПІДТВЕРДИТИ ЗАМОВЛЕННЯ</button>
      <div id="checkout-error" class="checkout-error" hidden></div>
    </form>
    <aside class="summary-card checkout-summary"><div class="eyebrow">ВАШЕ ЗАМОВЛЕННЯ</div>${cart.length?cart.map(x=>`<div class="checkout-line"><div><b>${x.p.name}</b><span>${x.sku.variant} · SKU ${x.sku.id}</span></div><span>${x.row.qty} × ${BB610.money(x.sku.price)}</span></div>`).join(''):'<div class="empty">Кошик порожній.</div>'}<div class="summary-row"><b>Разом</b><b>${cart.length&&cart.every(x=>x.sku.price!=null)?BB610.money(total):'Ціна уточнюється'}</b></div><p class="checkout-disclaimer">Фінальна сума, доступність і умови доставки підтверджуються backend під час створення замовлення.</p></aside>
  </div>`;

  const form=document.getElementById('checkout-form'), btn=document.getElementById('submit-order'), err=document.getElementById('checkout-error');
  form.addEventListener('submit',async e=>{
    e.preventDefault();
    if(!form.reportValidity()||!configured||!allOrderable)return;
    err.hidden=true;btn.disabled=true;btn.textContent='СТВОРЕННЯ ЗАМОВЛЕННЯ…';
    const fd=new FormData(form);
    const payload={
      customer:{name:String(fd.get('name')||'').trim(),phone:String(fd.get('phone')||'').trim(),email:String(fd.get('email')||'').trim()||null},
      fulfillment:{method:String(fd.get('method')||''),destination:String(fd.get('destination')||'').trim()||null},
      comment:String(fd.get('comment')||'').trim()||null,
      currency:'UAH',
      items:cart.map(x=>({sku:x.sku.id,quantity:x.row.qty})),
      source:{channel:'web',site:'market.bb610.com.ua'}
    };
    try{
      const result=await BB610OrderClient.createOrder(payload);
      sessionStorage.setItem('bb610_pending_order',JSON.stringify({order_id:result.order_id,public_token:result.public_token||null}));
      if(result.payment?.redirect_url){location.href=result.payment.redirect_url;return}
      const success=result.confirmation_url||`order/success/?order=${encodeURIComponent(result.order_id)}${result.public_token?`&token=${encodeURIComponent(result.public_token)}`:''}`;
      location.href=success;
    }catch(ex){
      err.hidden=false;err.textContent=ex.code==='BACKEND_NOT_CONFIGURED'?'Backend замовлень не налаштований.':(ex.data?.message||ex.message||'Не вдалося створити замовлення.');
      btn.disabled=false;btn.textContent='ПІДТВЕРДИТИ ЗАМОВЛЕННЯ';
    }
  });
});
