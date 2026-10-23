/* デッキまとめページの表示。データは decks.js（デッキ）と data/chars.json（キャラの数値） */
const ROOT=document.body.dataset.root||"";
const IMG=new Proxy({},{get:(_,k)=>`${ROOT}img/decks/${k}.jpg`});
let CHAR_LIST=[], CHAR={};
const SNS={x:"https://x.com/pawapuryotsu",yt:"https://www.youtube.com/@pawapuryotsu"};
const POSITIONS={roman:["先","中","抑"],andromeda:["捕","一","二","三","遊","外"]};
const PITCH=["先","中","抑"];

const SCHOOL_NAME={roman:"ロマン開花學園",andromeda:"アンドロメダ学園"};

const COLS={
  roman:[{label:"得意練習",src:"得意練習"},{label:"練習効果",src:"bonus",key:"練習効果アップ",unit:"%"},
         {label:"タッグボーナス",src:"bonus",key:"スペシャルタッグボーナス",unit:"%"}],
  andromeda:[{label:"コツボナ",src:"bonus",key:"コツイベントボーナス",unit:"%"},
         {label:"試合",src:"bonus",key:"試合経験点ボーナス",unit:"%"}]
};
const POS_GOLD={捕:["球界の頭脳"],一:["至高の一塁手"],二:["至高の二塁手"],三:["至高の三塁手"],遊:["至高の遊撃手"],外:["至高の外野手"],
  先:["至高のスターター","至高のリリーバー","至高のクローザー"],中:["至高のスターター","至高のリリーバー","至高のクローザー"],
  抑:["至高のスターター","至高のリリーバー","至高のクローザー"]};
const posGold=(c,pos)=>c?(POS_GOLD[pos]||[]).filter(g=>[...(c.金特?.投手||[]),...(c.金特?.野手||[])].includes(g)):[];
const REFORM={andromeda:[["筋力改革","筋力練習改革"],["走塁改革","走塁練習改革"]],roman:[["コン改革","コントロール練習改革"],["スタ改革","スタミナ練習改革"]]};
function hasReform(rows,prefix){
  return rows.some(([n,rar,lv])=>{const c=CHAR[n]; if(!c) return false;
    return Object.keys(c.bonus||{}).some(k=>k.startsWith(prefix)&&(lvValue(c.bonus[k].表示,rar,lv)||0)>0);});
}
function maxCap(rows){ return Math.max(0,...rows.map(([n,rar,lv])=>lvValue(CHAR[n]?.bonus?.["サポ：獲得経験点上限"]?.表示,rar,lv)||0)); }
function itemList(rows){ const items=[...new Set(rows.flatMap(([n])=>(CHAR[n]?.アイテム||[]).map(x=>x.名前)))];
  return items.length?`<ul class="items">${items.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:`<p class="muted">なし</p>`; }
function videoBlock(id){ if(!/^[\w-]{11}$/.test(id||"")) return `<p class="muted">準備中</p>`;
  const url=`https://youtu.be/${id}`;
  return `<button type="button" class="yt" data-id="${id}" aria-label="動画を再生"><img src="https://i.ytimg.com/vi/${id}/hqdefault.jpg" alt="動画のサムネイル" loading="lazy" onerror="this.parentNode.style.display='none'"><span class="play">▶</span></button>
    <a class="video" href="${url}" target="_blank" rel="noopener">YouTubeで見る</a>`; }
function reformLine(d){
  const rows=[...d.main,...d.sub];
  return `<p class="reform">${REFORM[state.school].map(([label,prefix])=>{const ok=hasReform(rows,prefix);return `<span class="${ok?"ok":"ng"}">${label} ${ok?"〇":"×"}</span>`}).join("")}</p>`;
}
const shortName=n=>{const c=CHAR[n]; return c&&c.二つ名?`[${c.二つ名}]${c.苗字}`:n;};
const SUPPORT_EXTRA={roman:[],andromeda:[]};


const fmt=n=>n.toLocaleString("ja-JP");
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const state={school:document.body.dataset.school,sort:"exp",pos:{},q:""};
const norm=s=>s.normalize("NFKC").toLowerCase().replace(/[\s　]/g,"").replace(/[ぁ-ゖ]/g,c=>String.fromCharCode(c.charCodeAt(0)+96));
const terms=()=>state.q.split(/[\s　]+/).map(norm).filter(Boolean);
/* キャラ名か読み仮名（ひらがな）のどちらかに含まれていれば一致 */
const matchesTerm=(name,t)=>norm(name).includes(t)||norm(CHAR[name]?.読み||"").includes(t);

function deckMatches(d){
  if(state.pos[d.pos]===false) return false;
  const all=[...d.main,...d.sub].map(x=>x[0]);
  return terms().every(t=>all.some(n=>matchesTerm(n,t)));
}
function lvValue(shown,rar,lv){
  const t=shown?.[rar]; if(!t) return null; let v=null;
  Object.keys(t).map(Number).sort((a,b)=>a-b).forEach(k=>{if(k<=lv)v=t[k]});
  return v;
}
function colValue(c,col,rar,lv){
  const sc=c.シナリオ別?.[SCHOOL_NAME[state.school]];
  if(col.src==="得意練習") return lvValue(sc?.得意練習?.表示,rar,lv) ?? (c.得意練習?.length?c.得意練習.join("・"):null);
  if(col.src==="bonus") return lvValue(c.bonus?.[col.key]?.表示,rar,lv);
  if(col.src==="シナリオ") return lvValue(sc?.[col.key]?.表示,rar,lv);
  return null;
}
function slotTable(rows,deckPos){
  const ts=terms(), cols=COLS[state.school];
  const body=rows.map(([name,rar,lv])=>{
    const c=CHAR[name]; const hit=ts.some(t=>matchesTerm(name,t));
    const cells=cols.map(col=>{
      const v=c?colValue(c,col,rar,lv):null;
      if(v==null) return `<td class="${col.unit?"num":""}">―</td>`;
      if(typeof v==="number") return `<td class="num">${v}${col.unit||""}</td>`;
      return `<td>${esc(v)}</td>`;}).join("");
    const g=posGold(c,deckPos); const star=g.length?`<span class="star" title="${esc(g.join("・"))}">☆</span>`:"";
    return `<tr><td class="name ${hit?"found":""}">${star}${esc(shortName(name))}${c?"":"（データなし）"}</td><td class="num rl">${rar}${lv}</td>${cells}</tr>`;
  }).join("");
  return `<div class="tablewrap"><table class="slots"><thead><tr><th>キャラ</th><th class="num">Lv</th>${cols.map(col=>`<th class="${col.unit?"num":""}">${col.label}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
}
function judge(c,deckPos){
  if(c.分類==="彼女"||c.分類==="相棒") return ["回復","heal"];
  const same=c.ポジション===deckPos||(c.ポジション==="投"&&PITCH.includes(deckPos));
  return same?["一致","ok"]:["不一致","ng"];
}
function supportTable(rows,deckPos){
  const ts=terms(), extra=SUPPORT_EXTRA[state.school];
  const body=rows.map(([name,rar,lv,opt])=>{
    const c=CHAR[name]||(opt&&{ポジション:opt.pos}); const hit=ts.some(t=>matchesTerm(name,t));
    const [jt,jc]=c?judge(c,deckPos):["―",""];
    const posText=c?(c.分類==="彼女"||c.分類==="相棒"?c.分類:(c.ポジション||"―")):"―";
    return `<tr><td class="name ${hit?"found":""}">${esc(shortName(name))}${c?"":"（データなし）"}</td><td class="num rl">${rar}${lv}</td><td>${esc(posText)}</td><td><span class="judge ${jc}">${jt}</span></td>${extra.map(e=>`<td>${c?esc(e.get(c)):"―"}</td>`).join("")}</tr>`;
  }).join("");
  return `<div class="tablewrap"><table class="slots"><thead><tr><th>キャラ</th><th class="num">Lv</th><th>守備</th><th>判定</th>${extra.map(e=>`<th>${e.label}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
}
function renderList(){
  const s=DECKS[state.school];
  const decks=s.list.filter(deckMatches).sort((a,b)=>b[state.sort]-a[state.sort]);
  const open=new Set([...document.querySelectorAll("details.deck[open]")].map(e=>e.dataset.id));
  document.getElementById("count").textContent=`${decks.length}件 / 全${s.list.length}件`;
  const ts=terms();
  document.getElementById("list").innerHTML=decks.length?decks.map(d=>{
    const id=d.d; const hits=[...new Set([...d.main,...d.sub].map(x=>x[0]).filter(n=>ts.some(t=>matchesTerm(n,t))))];
    return `<details class="deck" data-id="${id}" ${open.has(id)?"open":""}>
      <summary>
        <div class="top"><div class="lft"><img src="${IMG[d.r]}" alt="ポジション${d.pos}・選手ランク${d.rank}・総経験点${fmt(d.exp)}"></div><span class="chev" aria-hidden="true">▾</span></div>
        ${hits.length?`<div class="hit">検索に一致：${hits.map(h=>`<mark>${esc(h)}</mark>`).join(" ")}</div>`:""}
        <img class="deckimg" src="${IMG[d.d]}" alt="メインデッキ">
      </summary>
      ${d.s?`<img class="subdeck" src="${IMG[d.s]}" alt="サポートデッキ">`:`<div class="subimg">サポートデッキのスクショ</div>`}
      ${d.u?`<img class="baseimg" src="${IMG[d.u]}" alt="基礎上限">`:`<div class="subimg">基礎上限のスクショ</div>`}
      <div class="reformwrap">${reformLine(d)}<p class="cap">獲得経験点上限<b>${maxCap(d.sub)||"なし"}</b></p></div>
      <div class="detail">
        <div><h3>メインデッキ <small>☆＝このポジションの至高・球界の頭脳が取れる</small></h3>${slotTable(d.main,d.pos)}</div>
        <div><h3>追加アイテム</h3>${itemList(d.main)}</div>
        <div><h3>サポートデッキ</h3>${supportTable(d.sub,d.pos)}</div>
        <div><h3>育成のポイント</h3>${Array.isArray(d.tips)?`<ul class="tips">${d.tips.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:`<p>${d.tips}</p>`}</div>
        <div><h3>解説動画</h3>${videoBlock(d.video)}</div>
      </div></details>`}).join(""):s.list.length===0?`<div class="empty">このシナリオのデッキは準備中です。<br>掲載しだい <a href="${SNS.x}" target="_blank" rel="noopener">X</a> でお知らせします。</div>`:`<div class="empty">条件に合うデッキがありません。<br>ポジションのチェックやキャラ名を見直してください。</div>`;
}
document.addEventListener("click",e=>{const b=e.target.closest(".yt"); if(!b) return;
  b.outerHTML=`<div class="ytframe"><iframe src="https://www.youtube-nocookie.com/embed/${b.dataset.id}?autoplay=1" title="解説動画" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>`;});

function renderDecks(){
  const s=DECKS[state.school];
  const counts={}; s.list.forEach(d=>counts[d.pos]=(counts[d.pos]||0)+1);
  const names=[...new Set(s.list.flatMap(d=>[...d.main,...d.sub].map(x=>x[0])))].sort();
  document.getElementById("deckapp").innerHTML=`
    <section class="filters">
      <div><div class="flabel"><span>メインポジション</span><button id="allpos" type="button">すべて選択</button></div>
        <div class="posbox">${POSITIONS[state.school].map(p=>`<label class="${counts[p]?"":"zero"}"><input type="checkbox" value="${p}" ${state.pos[p]===false?"":"checked"}>${p}<small>${counts[p]||0}</small></label>`).join("")}</div></div>
      <div><div class="flabel"><span>キャラ名で探す</span></div>
        <div class="search"><input id="q" type="search" list="names" placeholder="例：山本 / やまもと" autocomplete="off" aria-label="キャラ名"><button id="clear" type="button">クリア</button></div>
        <datalist id="names">${names.map(n=>`<option value="${esc(n)}">`).join("")}</datalist>
        <div class="shelp">ひらがな（読み方）でも探せます。メイン・サポートのどちらかに入っているデッキを表示します。スペースで区切ると「両方入っている」デッキに絞れます。</div></div>
    </section>
    <div class="bar"><span id="count"></span>
      <label>並び順 <select id="sort"><option value="exp">総経験点が高い順</option><option value="rank">選手ランクが高い順</option></select></label></div>
    <div class="list" id="list"></div>`;
  const sel=document.getElementById("sort"); sel.value=state.sort;
  sel.onchange=()=>{state.sort=sel.value;renderList()};
  document.querySelectorAll(".posbox input").forEach(cb=>cb.onchange=()=>{state.pos[cb.value]=cb.checked;renderList()});
  document.getElementById("allpos").onclick=()=>{state.pos={};document.querySelectorAll(".posbox input").forEach(cb=>cb.checked=true);renderList()};
  const q=document.getElementById("q"); q.oninput=()=>{state.q=q.value;renderList()};
  document.getElementById("clear").onclick=()=>{q.value="";state.q="";renderList()};
  renderList();
}
fetch(`${ROOT}data/chars.json`).then(r=>r.json()).catch(()=>[]).then(list=>{
  CHAR_LIST=list; CHAR=Object.fromEntries(list.map(c=>[c.name,c]));
  renderDecks();
});
