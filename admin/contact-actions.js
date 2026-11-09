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
window.BB610_CONTACT={normalizePhone,links,copy,buttonHtml};
})();