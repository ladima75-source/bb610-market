document.addEventListener('DOMContentLoaded',async()=>{
  await BB610_DATA_SOURCE.refresh();
  const ids=BB610.get(BB610.LS.fav,[]);
  const ps=ids.map(BB610.byId).filter(Boolean);
  const grid=document.getElementById('fav-grid');
  grid.innerHTML=ps.map(BB610.cardV2).join('');
  document.getElementById('fav-empty').style.display=ps.length?'none':'block';
  BB610.bindCards(grid);
});
