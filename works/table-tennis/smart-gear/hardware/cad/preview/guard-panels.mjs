const panels=[...document.querySelectorAll('.panel')];let z=20,active=null;const key='guard-workbench-panels-v1';let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}');}catch{}
for(const svg of document.querySelectorAll('svg'))svg.setAttribute('aria-hidden','true');
for(const b of document.querySelectorAll('[data-panel]'))b.setAttribute('aria-haspopup','dialog');
function clamp(panel,x,y){return [Math.max(72,Math.min(innerWidth-panel.offsetWidth-8,x)),Math.max(78,Math.min(innerHeight-80,y))];}
function position(panel,x,y){const [a,b]=clamp(panel,x,y);panel.style.left=a+'px';panel.style.top=b+'px';}
function save(panel){saved[panel.id]={x:parseFloat(panel.style.left),y:parseFloat(panel.style.top)};try{localStorage.setItem(key,JSON.stringify(saved));}catch{}}
function placeWithoutOverlap(p,x,y){
 const others=panels.filter(q=>q!==p&&!q.hidden),w=p.offsetWidth,h=p.offsetHeight,gap=12;
 const fits=(a,b)=>a>=72&&b>=78&&a+w<=innerWidth-8&&b+h<=innerHeight-65&&others.every(q=>{const r=q.getBoundingClientRect();return a+w+gap<=r.left||a>=r.right+gap||b+h+gap<=r.top||b>=r.bottom+gap;});
 const candidates=[[x,y],[104,90],[innerWidth-w-12,90]];
 for(let b=90;b+h<=innerHeight-65;b+=24)for(let a=88;a+w<=innerWidth-8;a+=24)candidates.push([a,b]);
 candidates.sort((a,b)=>Math.hypot(a[0]-x,a[1]-y)-Math.hypot(b[0]-x,b[1]-y));
 const slot=candidates.find(([a,b])=>fits(a,b));
 if(slot){position(p,...slot);return;}
 // A small viewport cannot hold every dialog: make room, preserving saved homes.
 const oldest=others.sort((a,b)=>Number(a.style.zIndex)-Number(b.style.zIndex))[0];
 if(oldest){hide(oldest);placeWithoutOverlap(p,x,y);}else position(p,x,y);
}
function hide(p){p.hidden=true;p.dataset.open='false';document.querySelector(`[data-panel="${p.id.replace('panel-','')}"]`).setAttribute('aria-expanded','false');}
function show(id,open){const p=document.querySelector('#panel-'+id),button=document.querySelector(`[data-panel="${id}"]`);if(!open){hide(p);button.focus();active=null;return;}p.hidden=false;p.dataset.open='true';button.setAttribute('aria-expanded','true');p.style.zIndex=++z;active=p;const s=saved[p.id],right=id==='help'||id==='data';placeWithoutOverlap(p,s?.x??(right?innerWidth-330:104),s?.y??90);}

for(const button of document.querySelectorAll('[data-panel]'))button.onclick=()=>show(button.dataset.panel,document.querySelector('#panel-'+button.dataset.panel).hidden);
for(const p of panels){p.querySelector('[data-close]').onclick=()=>show(p.id.replace('panel-',''),false);const header=p.querySelector('header');let drag=null;header.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;active=p;p.style.zIndex=++z;drag={x:e.clientX,y:e.clientY,left:p.offsetLeft,top:p.offsetTop};header.setPointerCapture(e.pointerId);});header.addEventListener('pointermove',e=>{if(drag)position(p,drag.left+e.clientX-drag.x,drag.top+e.clientY-drag.y);});header.addEventListener('pointerup',()=>{if(drag){drag=null;save(p);}});header.addEventListener('pointercancel',()=>drag=null);header.addEventListener('keydown',e=>{const moves={ArrowLeft:[-10,0],ArrowRight:[10,0],ArrowUp:[0,-10],ArrowDown:[0,10]};if(moves[e.key]){e.preventDefault();position(p,p.offsetLeft+moves[e.key][0],p.offsetTop+moves[e.key][1]);save(p);}});p.addEventListener('pointerdown',()=>{active=p;p.style.zIndex=++z;});}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&active)show(active.id.replace('panel-',''),false);});
for(const b of document.querySelectorAll('[data-for]')){b.tabIndex=b.getAttribute('aria-checked')==='true'?0:-1;b.onclick=()=>{const id=b.dataset.for,input=document.getElementById(id);input.value=b.dataset.value;for(const sibling of document.querySelectorAll(`[data-for="${id}"]`)){sibling.setAttribute('aria-checked',String(sibling===b));sibling.tabIndex=sibling===b?0:-1;}input.dispatchEvent(new Event('input',{bubbles:true}));};b.onkeydown=e=>{const group=[...document.querySelectorAll(`[data-for="${b.dataset.for}"]`)];let i=group.indexOf(b);if(['ArrowDown','ArrowRight'].includes(e.key))i=(i+1)%group.length;else if(['ArrowUp','ArrowLeft'].includes(e.key))i=(i+group.length-1)%group.length;else if(e.key==='Home')i=0;else if(e.key==='End')i=group.length-1;else return;e.preventDefault();group[i].click();group[i].focus();};}
for(const b of document.querySelectorAll('[data-toggle]'))b.onclick=()=>{const input=document.getElementById(b.dataset.toggle);input.checked=!input.checked;b.setAttribute('aria-checked',String(input.checked));input.dispatchEvent(new Event('input',{bubbles:true}));};
for(const p of panels)p.addEventListener('focusin',()=>{active=p;p.style.zIndex=++z;});
addEventListener('resize',()=>{for(const p of panels)if(!p.hidden)position(p,p.offsetLeft,p.offsetTop);});
show('load',innerWidth>=650);
