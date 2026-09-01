document.addEventListener('DOMContentLoaded',async()=>{
  const root=document.getElementById('order-success-app'); if(!root)return;
  const q=new URLSearchParams(location.search); let orderId=q.get('order'),token=q.get('token');
  if(!orderId){try{const p=JSON.parse(sessionStorage.getItem('bb610_pending_order')||'null');orderId=p?.order_id;token=token||p?.public_token}catch{}}
  if(!BB610OrderClient.configured()){
    root.innerHTML='<div class="order-state"><div class="eyebrow">ORDER CONFIRMATION</div><h1>Backend ще не підключений</h1><p>Ця сторінка вже підготовлена для підтвердження реального замовлення. Подія <code>purchase</code> у статичному режимі не відправляється.</p><a class="btn secondary" href="../../index.html">НА ГОЛОВНУ</a></div>';return;
  }
  if(!orderId){root.innerHTML='<div class="order-state"><h1>Замовлення не знайдено</h1><p>Немає ідентифікатора замовлення.</p></div>';return}
  root.innerHTML='<div class="order-state"><h1>Перевіряємо замовлення…</h1></div>';
  try{
    const o=await BB610OrderClient.getOrder(orderId,token);
    const tx=o.transaction_id||o.order_id;
    if(o.analytics?.purchase_ready===true&&tx){
      const marker=`bb610_purchase_sent:${tx}`;
      if(!localStorage.getItem(marker)){
        BB610.pushEvent('purchase',{event_id:o.analytics?.event_id||`purchase:${tx}`,ecommerce:{transaction_id:tx,value:Number(o.total),currency:o.currency||'UAH',items:(o.items||[]).map(i=>({item_id:i.sku,item_name:i.name,item_brand:i.brand,item_category:i.category,item_variant:i.variant,price:Number(i.unit_price),quantity:Number(i.quantity),currency:o.currency||'UAH'}))}});
        localStorage.setItem(marker,new Date().toISOString());
      }
    }
    if(o.clear_cart===true){BB610.set(BB610.LS.cart,[]);BB610.updateBadges()}
    BB610OrderClient.resetRequestId();sessionStorage.removeItem('bb610_pending_order');
    const ins=o.payment?.method==='bank_transfer'?(o.payment?.instructions||{}):null;const bank=ins&&ins.iban?`<div class="payment-instructions"><div class="eyebrow">ОПЛАТА НА РАХУНОК</div><p><b>Отримувач:</b> ${String(ins.recipient||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}</p><p><b>IBAN:</b> <code>${String(ins.iban||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}</code></p><p><b>Призначення:</b> ${String(ins.purpose||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}</p><small>Замовлення буде передано в роботу після підтвердження оплати.</small></div>`:'';root.innerHTML=`<div class="order-state success"><div class="eyebrow">ЗАМОВЛЕННЯ ПРИЙНЯТО</div><h1>Дякуємо</h1><p>Номер замовлення: <b>${o.order_number||o.order_id}</b></p><p>${o.customer_message||'Ми отримали замовлення та зв’яжемося з вами щодо підтвердження.'}</p>${bank}<a class="btn" href="../../index.html">ПОВЕРНУТИСЯ ДО МАГАЗИНУ</a></div>`;
  }catch(ex){root.innerHTML=`<div class="order-state"><h1>Не вдалося підтвердити замовлення</h1><p>${ex.message||'Спробуйте відкрити сторінку пізніше.'}</p></div>`}
});
