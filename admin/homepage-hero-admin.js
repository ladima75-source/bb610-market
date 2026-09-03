
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const token=()=>localStorage.getItem('bb610_admin_token')||document.querySelector('#token')?.value||'';
async function api(path,opt={}){const r=await fetch(API+path,{...opt,headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json',...(opt.headers||{})}});const x=await r.json().catch(()=>({detail:'Unknown error'}));if(!r.ok)throw new Error(x.detail||JSON.stringify(x));return x}
let data=null,selected='';

function mount(){
  if(document.querySelector('.bb19a3-hero-admin'))return;
  const h1=[...document.querySelectorAll('h1')].find(x=>/Головна\s*\/\s*Вітрина/i.test(x.textContent||''));
  const anchor=h1?.closest('main')?.querySelector('.head') || h1?.parentElement || document.querySelector('main');
  if(!anchor)return;
  const box=document.createElement('section');box.className='bb19a3-hero-admin';
  box.innerHTML=`
    <div><h2>Головний банер / HERO</h2><div class=sub>Зображення з медіатеки, текст і кнопка керуються тут.</div></div>
    <div class=bb19a3-grid>
      <div>
        <div class=bb19a3-fields>
          <label class="bb19a3-check wide"><input id=hEnabled type=checkbox> Увімкнено</label>
          <label class=wide>Зображення<input id=hImage placeholder="assets/media/..."></label>
          <label>Заголовок<input id=hTitle placeholder="Необов’язково"></label>
          <label>Підзаголовок<input id=hSubtitle placeholder="Необов’язково"></label>
          <label>Текст кнопки<input id=hBtnText placeholder="Напр. Перейти до каталогу"></label>
          <label>Посилання кнопки<input id=hBtnUrl placeholder="catalog.html"></label>
          <label>Вирівнювання<select id=hAlign><option value=left>Ліворуч</option><option value=center>По центру</option><option value=right>Праворуч</option></select></label>
          <label class=bb19a3-check><input id=hOverlay type=checkbox> Затемнення під текстом</label>
        </div>
        <div class=bb19a3-actions><button id=hSave class=bb19a3-primary>Зберегти та опублікувати HERO</button></div>
        <div class=bb19a3-preview id=hPreview></div>
      </div>
      <div>
        <div style="color:#8e9ca3;font-size:10px;margin-bottom:7px">Вибрати з медіатеки</div>
        <div class=bb19a3-media id=hMedia></div>
      </div>
    </div>`;
  const notice=anchor.nextElementSibling;
  if(notice) anchor.parentElement.insertBefore(box,notice); else anchor.parentElement.appendChild(box);

  ['hImage','hTitle','hSubtitle','hBtnText','hBtnUrl','hAlign','hOverlay','hEnabled'].forEach(id=>{
    $('#'+id)?.addEventListener(id==='hAlign'||id==='hOverlay'||id==='hEnabled'?'change':'input',preview)
  });
  $('#hSave').onclick=save;
  load();
}
function heroFromForm(){return {enabled:$('#hEnabled').checked,image:$('#hImage').value.trim(),title:$('#hTitle').value.trim(),subtitle:$('#hSubtitle').value.trim(),button_text:$('#hBtnText').value.trim(),button_url:$('#hBtnUrl').value.trim()||'catalog.html',align:$('#hAlign').value,overlay:$('#hOverlay').checked}}
function fill(h){$('#hEnabled').checked=!!h.enabled;$('#hImage').value=h.image||'';$('#hTitle').value=h.title||'';$('#hSubtitle').value=h.subtitle||'';$('#hBtnText').value=h.button_text||'';$('#hBtnUrl').value=h.button_url||'catalog.html';$('#hAlign').value=h.align||'left';$('#hOverlay').checked=h.overlay!==false;selected=h.image||'';renderMedia();preview()}
function preview(){const h=heroFromForm();const cls=h.align==='center'?'center':h.align==='right'?'right':'';$('#hPreview').innerHTML=h.image?`<img src="/${esc(h.image.replace(/^\/+/,''))}"><div class="bb19a3-preview-copy ${cls}"><div class=bb19a3-preview-content>${h.title?`<h3>${esc(h.title)}</h3>`:''}${h.subtitle?`<p>${esc(h.subtitle)}</p>`:''}${h.button_text?`<b>${esc(h.button_text)}</b>`:''}</div></div>`:'<div style="padding:20px;color:#77858b">Зображення не вибрано.</div>'}
function renderMedia(){const arr=data?.media||[];$('#hMedia').innerHTML=arr.map(m=>`<div class="bb19a3-media-card ${m.url===selected?'active':''}" data-url="${esc(m.url)}"><img src="/${esc(m.url.replace(/^\/+/,''))}" alt=""><span>${esc(m.name)}</span></div>`).join('')||'<div style="color:#77858b;font-size:10px">У медіатеці немає доступних зображень.</div>';document.querySelectorAll('.bb19a3-media-card').forEach(c=>c.onclick=()=>{selected=c.dataset.url;$('#hImage').value=selected;renderMedia();preview()})}
async function load(){try{data=await api('/api/v1/admin/homepage-hero');fill(data.hero||{})}catch(e){alert(e.message)}}
async function save(){if(!confirm('Зберегти HERO та опублікувати?'))return;try{const x=await api('/api/v1/admin/homepage-hero',{method:'POST',body:JSON.stringify({hero:heroFromForm(),publish_git:true})});alert('HERO опубліковано'+(x.commit?' · '+x.commit:''));data.hero=x.hero;fill(x.hero)}catch(e){alert(e.message)}}
setTimeout(mount,100);
})();
