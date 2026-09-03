
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const token=()=>localStorage.getItem('bb610_admin_token')||document.querySelector('#token')?.value||'';
const imgUrl=p=>encodeURI('/'+String(p||'').replace(/^\/+/,''));
async function api(path,opt={}){const r=await fetch(API+path,{...opt,headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json',...(opt.headers||{})}});const x=await r.json().catch(()=>({detail:'Невідома помилка'}));if(!r.ok)throw new Error(x.detail||JSON.stringify(x));return x}
let data=null,selected='';

function mount(){
 if(document.querySelector('.bb19a5-hero-admin'))return;
 const old=document.querySelector('.bb19a3-hero-admin');if(old)old.remove();
 const h1=[...document.querySelectorAll('h1')].find(x=>/Головна\s*\/\s*Вітрина/i.test(x.textContent||''));
 const anchor=h1?.parentElement||document.querySelector('main');if(!anchor)return;
 const box=document.createElement('section');box.className='bb19a3-hero-admin bb19a5-hero-admin';
 box.innerHTML=`<div><h2>Головний банер / HERO</h2><div class=sub>Зображення, текст, акцент і типографіка керуються тут.</div></div>
 <div class=bb19a3-grid><div><div class=bb19a3-fields>
 <label class="bb19a3-check wide"><input id=hEnabled type=checkbox> Увімкнено</label>
 <label class=wide>Зображення з медіатеки<input id=hSource readonly placeholder="Виберіть праворуч"></label>
 <label>Заголовок<input id=hTitle placeholder="Напр. Професійні товари"></label>
 <label>Акцентний текст<input id=hAccent placeholder="Напр. для вирощування"></label>
 <label class=wide>Підзаголовок<input id=hSubtitle placeholder="Необов’язково"></label>
 <label>Текст кнопки<input id=hBtnText placeholder="Перейти до каталогу"></label><label>Посилання кнопки<input id=hBtnUrl placeholder="catalog.html"></label>
 <label>Вирівнювання<select id=hAlign><option value=left>Ліворуч</option><option value=center>По центру</option><option value=right>Праворуч</option></select></label>
 <label class=bb19a3-check><input id=hOverlay type=checkbox> Затемнення під текстом</label>
 <div class=bb19a5-color-row>
   <label class=bb19a5-color>Колір заголовка<input id=hTitleColor type=color value="#ffffff"></label>
   <label class=bb19a5-color>Колір акценту<input id=hAccentColor type=color value="#86b93e"></label>
   <label class=bb19a5-color>Колір підзаголовка<input id=hSubtitleColor type=color value="#d1d7d2"></label>
 </div>
 <div class=bb19a5-size-row>
   <label>Розмір заголовка, px<input id=hTitleSize type=number min=32 max=88 step=1 value=56></label>
   <label>Розмір підзаголовка, px<input id=hSubtitleSize type=number min=12 max=30 step=1 value=17></label>
 </div></div>
 <div class=bb19a3-actions><button id=hSave class=bb19a3-primary>Зберегти та опублікувати HERO</button></div>
 <div class=bb19a3-preview id=hPreview></div></div>
 <div><div style="color:#8e9ca3;font-size:10px;margin-bottom:7px">Вибрати з медіатеки</div><div class=bb19a3-media id=hMedia></div></div></div>`;
 anchor.insertAdjacentElement('afterend',box);

 ['hTitle','hAccent','hSubtitle','hBtnText','hBtnUrl','hAlign','hOverlay','hEnabled','hTitleColor','hAccentColor','hSubtitleColor','hTitleSize','hSubtitleSize'].forEach(id=>{
   $('#'+id)?.addEventListener(['hAlign','hOverlay','hEnabled'].includes(id)?'change':'input',preview)
 });
 $('#hSave').onclick=save;load();
}

function form(){return {
 enabled:$('#hEnabled').checked,source_image:$('#hSource').value.trim(),
 title:$('#hTitle').value.trim(),accent_text:$('#hAccent').value.trim(),subtitle:$('#hSubtitle').value.trim(),
 button_text:$('#hBtnText').value.trim(),button_url:$('#hBtnUrl').value.trim()||'catalog.html',
 align:$('#hAlign').value,overlay:$('#hOverlay').checked,
 title_color:$('#hTitleColor').value,accent_color:$('#hAccentColor').value,subtitle_color:$('#hSubtitleColor').value,
 title_size:Number($('#hTitleSize').value||56),subtitle_size:Number($('#hSubtitleSize').value||17)
}}
function fill(h){$('#hEnabled').checked=!!h.enabled;selected=h.source_image||h.image||'';$('#hSource').value=selected;$('#hTitle').value=h.title||'';$('#hAccent').value=h.accent_text||'';$('#hSubtitle').value=h.subtitle||'';$('#hBtnText').value=h.button_text||'';$('#hBtnUrl').value=h.button_url||'catalog.html';$('#hAlign').value=h.align||'left';$('#hOverlay').checked=h.overlay!==false;$('#hTitleColor').value=h.title_color||'#ffffff';$('#hAccentColor').value=h.accent_color||'#86b93e';$('#hSubtitleColor').value=h.subtitle_color||'#d1d7d2';$('#hTitleSize').value=h.title_size||56;$('#hSubtitleSize').value=h.subtitle_size||17;renderMedia();preview()}
function renderMedia(){const arr=data?.media||[];$('#hMedia').innerHTML=arr.map(m=>`<div class="bb19a3-media-card ${m.url===selected?'active':''} ${m.exists?'':'missing'}" data-url="${esc(m.url)}">${m.exists?`<img src="${imgUrl(m.url)}" alt="">`:'<div class=bb19a4-missing>Файл відсутній</div>'}<span>${esc(m.name)}${m.exists?'':' · MISSING'}</span></div>`).join('')||'<div style="color:#77858b;font-size:10px">Немає зображень.</div>';document.querySelectorAll('.bb19a3-media-card').forEach(c=>c.onclick=()=>{if(c.classList.contains('missing'))return alert('Файл відсутній на сервері.');selected=c.dataset.url;$('#hSource').value=selected;renderMedia();preview()})}
function preview(){const h=form(),cls=h.align==='center'?'center':h.align==='right'?'right':'';$('#hPreview').innerHTML=h.source_image?`<img src="${imgUrl(h.source_image)}"><div class="bb19a3-preview-copy ${cls}"><div class=bb19a3-preview-content>${h.title?`<h3 style="color:${h.title_color};font-size:${Math.max(14,h.title_size*.38)}px">${esc(h.title)}</h3>`:''}${h.accent_text?`<h3 style="color:${h.accent_color};font-size:${Math.max(14,h.title_size*.38)}px;margin-top:3px">${esc(h.accent_text)}</h3>`:''}${h.subtitle?`<p style="color:${h.subtitle_color};font-size:${Math.max(8,h.subtitle_size*.6)}px">${esc(h.subtitle)}</p>`:''}${h.button_text?`<b>${esc(h.button_text)}</b>`:''}</div></div>`:'<div style="padding:20px;color:#77858b">Зображення не вибрано.</div>'}
async function load(){try{data=await api('/api/v1/admin/homepage-hero');fill(data.hero||{})}catch(e){alert(e.message)}}
async function save(){const h=form();if(h.enabled&&!h.source_image)return alert('Спочатку виберіть зображення');if(!confirm('Зберегти та опублікувати HERO?'))return;try{const x=await api('/api/v1/admin/homepage-hero',{method:'POST',body:JSON.stringify({hero:h,publish_git:true})});alert('HERO опубліковано'+(x.commit?' · '+x.commit:''));data.hero=x.hero;fill(x.hero)}catch(e){alert(e.message)}}
setTimeout(mount,140);
})();
