(()=>{'use strict';
function normalizePhone(value){
  let digits=String(value||'').replace(/\D/g,'');
  if(/^0\d{9}$/.test(digits))digits='38'+digits;
  if(/^80\d{9}$/.test(digits))digits='3'+digits;
  return /^380\d{9}$/.test(digits)?digits:'';
}
function links(phone,message){
  const n=normalizePhone(phone);
  const draft=encodeURIComponent(String(message||''));
  if(!n)return {phone:'',whatsapp:'',telegram:'',sms:''};
  return {
    phone:n,
    whatsapp:'https://wa.me/'+n+'?text='+draft,
    telegram:'https://t.me/+'+n+'?text='+draft,
    sms:'sms:+'+n+';?&body='+draft,
  };
}
async function copy(text){
  const value=String(text||'');
  if(navigator.clipboard?.writeText){
    try{await navigator.clipboard.writeText(value);return true}catch(_){}
  }
  const ta=document.createElement('textarea');
  ta.value=value;ta.style.position='fixed';ta.style.opacity='0';ta.style.pointerEvents='none';
  document.body.appendChild(ta);ta.focus();ta.select();
  let ok=false;try{ok=document.execCommand('copy')}catch(_){}
  ta.remove();return !!ok;
}
function buttonHtml(phone,message,idPrefix='contact'){
  const l=links(phone,message);
  const safe=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const copyBtn='<button type="button" class="contact-action secondary" data-contact-copy="'+safe(idPrefix)+'">Скопіювати</button>';
  if(!l.phone)return copyBtn+'<span class="contact-action-note">Перевірте номер телефону.</span>';
  return copyBtn+
    '<a class="contact-action" data-contact-whatsapp="'+safe(idPrefix)+'" href="'+safe(l.whatsapp)+'" target="_blank" rel="noopener noreferrer">WhatsApp</a>'+
    '<a class="contact-action" data-contact-telegram="'+safe(idPrefix)+'" href="'+safe(l.telegram)+'" target="_blank" rel="noopener noreferrer">Telegram</a>'+
    '<a class="contact-action" data-contact-sms="'+safe(idPrefix)+'" href="'+safe(l.sms)+'">SMS</a>';
}
function bindComposer(root,{phone,textareaSelector='[data-contact-message]',stateSelector='[data-contact-state]',prefix='contact'}={}){
  const ta=root?.querySelector(textareaSelector);
  const state=root?.querySelector(stateSelector);
  if(!ta)return;
  const refresh=()=>{
    const l=links(phone,ta.value);
    const wa=root.querySelector('[data-contact-whatsapp="'+prefix+'"]');
    const tg=root.querySelector('[data-contact-telegram="'+prefix+'"]');
    const sms=root.querySelector('[data-contact-sms="'+prefix+'"]');
    if(wa)wa.href=l.whatsapp||'#';
    if(tg)tg.href=l.telegram||'#';
    if(sms)sms.href=l.sms||'#';
  };
  ta.addEventListener('input',refresh);refresh();
  const copyBtn=root.querySelector('[data-contact-copy="'+prefix+'"]');
  if(copyBtn)copyBtn.onclick=async()=>{
    const ok=await copy(ta.value);
    if(state)state.textContent=ok?'✓ Текст скопійовано. Не відправлено.':'Не вдалося скопіювати текст.';
  };
  root.querySelectorAll('[data-contact-whatsapp="'+prefix+'"],[data-contact-telegram="'+prefix+'"],[data-contact-sms="'+prefix+'"]').forEach(a=>{
    a.addEventListener('click',()=>{if(state)state.textContent='Відкрито зовнішній канал. Надсилання підтвердіть у месенджері.'});
  });
}
window.BB610_CONTACT={normalizePhone,links,copy,buttonHtml,bindComposer};
})();