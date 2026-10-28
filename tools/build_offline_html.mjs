import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from './vendor/marked.esm.js';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = fs.readFileSync(path.join(repo, 'docs/新人保护指南-完整阅读版.md'), 'utf8');
const cover = fs.readFileSync(path.join(repo, 'assets/cover.png')).toString('base64');
const start = source.indexOf('## 开篇：');
if (start < 0) throw new Error('缺少开篇');
const body = source.slice(start);
const boundary = /^<a id="(chapter-\d+|appendix-[a-k])"><\/a>\s*$/gm;
const found = [...body.matchAll(boundary)];
if (found.length !== 25) throw new Error(`章节与附录数量错误：${found.length}`);

const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const segments = [{id:'intro', text:body.slice(0,found[0].index), name:'阅读入口', type:'intro'}];
for (let i=0;i<found.length;i++) {
  const id=found[i][1];
  const end=i+1<found.length ? found[i+1].index : body.length;
  let text=body.slice(found[i].index,end);
  if(id==='chapter-14') text=text.replace(/\n---\n\n## 附录\n\s*$/,'\n');
  const heading=text.match(/^## (.+)$/m);
  if(!heading) throw new Error(`没有标题：${id}`);
  segments.push({id,text,name:heading[1],type:id.startsWith('chapter')?'chapter':'appendix'});
}

const counts={intro:0,chapter:0,appendix:0};
const items=[];
for(const segment of segments){
  counts[segment.type]++;
  const matches=[...segment.text.matchAll(/^<a id="(item-[\d-]+)"><\/a>\s*\n\s*### (.+)$/gm)];
  for(let i=0;i<matches.length;i++){
    const m=matches[i];
    const next=i+1<matches.length?matches[i+1].index:segment.text.length;
    const chunk=segment.text.slice(m.index,next);
    items.push({id:m[1],title:m[2],section:segment.id,group:segment.name,text:chunk.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim()});
  }
}
if(counts.chapter!==14||counts.appendix!==11||items.length!==234) throw new Error(`内容数量不符 ${JSON.stringify(counts)} ${items.length}`);

const sections=segments.map(s=>`<section class="doc-section" id="section-${s.id}" data-section="${s.id}"${s.id==='intro'?'':' hidden'}>${marked.parse(s.text,{gfm:true,breaks:false})}</section>`).join('\n');
let lastType='';
const nav=segments.map(s=>{
  const heading=s.type!==lastType?`<div class="nav-group-title">${s.type==='intro'?'开始阅读':s.type==='chapter'?'14 章正文':'附录 A—K'}</div>`:'';
  lastType=s.type;
  return heading+`<button class="chapter-btn" type="button" data-go="${s.id}" aria-label="查看${escapeHtml(s.name)}"><span class="chapter-num">${s.id==='intro'?'·':s.id.startsWith('chapter-')?String(Number(s.id.split('-')[1])).padStart(2,'0'):s.id.slice(-1).toUpperCase()}</span><span>${escapeHtml(s.name.replace(/^第 \d+ 章 /,'').replace(/^[A-K]\. /,''))}</span></button>`;
}).join('\n');
const searchRecords=[...items];
for(const s of segments){
  if(s.id==='intro'||(s.type==='appendix'&&!items.some(x=>x.section===s.id))){
    searchRecords.push({id:s.id==='intro'?'section-intro':s.id,title:s.name,section:s.id,group:'阅读入口与附录',text:s.text.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim()});
  }
}
const indexJson=JSON.stringify(searchRecords).replace(/</g,'\\u003c');
const segmentJson=JSON.stringify(segments.map(({id,name,type})=>({id,name,type}))).replace(/</g,'\\u003c');
const template=fs.readFileSync(path.join(repo,'tools/offline_template.html'),'utf8');
const output=template
  .replaceAll('@@COVER@@',`data:image/png;base64,${cover}`)
  .replaceAll('@@SECTIONS@@',sections)
  .replaceAll('@@NAV@@',nav)
  .replaceAll('@@INDEX@@',indexJson)
  .replaceAll('@@SEGMENTS@@',segmentJson)
  .replaceAll('@@ITEM_COUNT@@',String(items.length));
if(output.includes('@@')) throw new Error('模板占位符未替换');
const repoHtml=path.join(repo,'index.html');
if(process.argv.includes('--check')){
  if(fs.readFileSync(repoHtml,'utf8')!==output)throw new Error('index.html 与阅读版正文不同步，请运行 node tools/build_offline_html.mjs');
  console.log('离线 HTML 与阅读版正文一致');
}else{
  fs.writeFileSync(repoHtml,output,'utf8');
  console.log(JSON.stringify({repoHtml,chapters:counts.chapter,appendices:counts.appendix,items:items.length,bytes:Buffer.byteLength(output)}));
}
