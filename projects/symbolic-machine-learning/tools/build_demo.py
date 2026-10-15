"""Build dependency-free English and Korean interactive views of the exported model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

WORDS = {
    "en": {
        "title": "Follow a learned symbolic decision",
        "eyebrow": "SYMBOLIC MACHINE LEARNING",
        "intro": "Change an input and follow the actual learned tree. The logical expression independently computes the same decision.",
        "scope": "Explanatory model fitted to all eight Boolean inputs. This is not a held-out performance measurement.",
        "inputs": "Choose the input",
        "tree": "Learned decision tree",
        "path": "Traversed conditions",
        "logic": "Equivalent logical expression",
        "result": "Prediction",
        "agreement": "Tree and logical expression agree",
        "disagreement": "Tree and logical expression disagree",
        "table": "All eight training inputs",
        "tableNote": "Select any row. The last column is the stored training label, not a new evaluation score.",
        "selection": "Select",
        "label": "Training label",
        "treeResult": "Tree",
        "logicResult": "Logic",
        "true": "True",
        "false": "False",
        "branch": "branch",
        "leaf": "leaf",
        "matching": "The highlighted terms match this input.",
        "none": "No positive term matches this input.",
        "source": "The page embeds examples/explanation.json. It runs offline without a server, downloads or external dependencies.",
        "counterpart": "한국어",
        "counterpartFile": "index.ko.html",
        "return": "Project explanation",
        "nodes": "nodes",
        "depth": "depth",
        "noscript": "Enable JavaScript to explore the learned model.",
    },
    "ko": {
        "title": "학습한 규칙의 판단 과정을 따라가 보세요",
        "eyebrow": "기호 머신러닝",
        "intro": "입력을 바꾸면 실제 학습한 트리의 경로가 표시됩니다. 논리식도 독립적으로 계산해 같은 판단을 하는지 확인합니다.",
        "scope": "불리언 입력 여덟 개 전체로 학습한 설명용 모델입니다. 홀드아웃 성능 평가가 아닙니다.",
        "inputs": "입력 선택",
        "tree": "학습한 결정 트리",
        "path": "실제로 따라간 조건",
        "logic": "같은 판단을 하는 논리식",
        "result": "예측 결과",
        "agreement": "트리와 논리식의 예측이 같습니다",
        "disagreement": "트리와 논리식의 예측이 다릅니다",
        "table": "전체 학습 입력 여덟 개",
        "tableNote": "행을 선택해 입력을 바꿀 수 있습니다. 마지막 열은 저장된 학습 정답이며 새로운 평가 점수가 아닙니다.",
        "selection": "선택",
        "label": "학습 정답",
        "treeResult": "트리",
        "logicResult": "논리식",
        "true": "참",
        "false": "거짓",
        "branch": "분기",
        "leaf": "리프",
        "matching": "강조한 조건이 현재 입력과 일치합니다.",
        "none": "현재 입력과 일치하는 양성 조건이 없습니다.",
        "source": "examples/explanation.json을 페이지 안에 포함했습니다. 서버나 추가 다운로드, 외부 의존성 없이 오프라인으로 실행합니다.",
        "counterpart": "English",
        "counterpartFile": "index.html",
        "return": "프로젝트 설명으로",
        "nodes": "노드",
        "depth": "깊이",
        "noscript": "학습한 모델을 조작하려면 JavaScript를 활성화하세요.",
    },
}

TEMPLATE = r'''<!doctype html>
<html lang="__LANG__">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{color-scheme:light;--ink:#242d39;--muted:#626875;--amber:#a97422;--cream:#f8f2e4;--line:#d8cfbb;--active:#efdbac}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:16px/1.65 system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif}
main{max-width:1160px;margin:auto;padding:42px 28px 56px}nav{display:flex;justify-content:space-between;gap:16px;align-items:center;font-size:13px}nav span{letter-spacing:.13em;font-weight:750}a{color:#835813;text-underline-offset:4px}h1{font-size:clamp(28px,4vw,43px);line-height:1.3;letter-spacing:-.035em;max-width:900px;margin:28px 0 16px}h2{font-size:20px;line-height:1.4;margin:0 0 16px}p{margin:0 0 16px}.intro{max-width:850px;color:var(--muted)}.scope{border-left:4px solid var(--amber);background:#ead8b440;padding:13px 18px;margin-top:24px;font-size:14px}.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,.7fr);gap:20px;margin:26px 0}.card{border:1px solid var(--line);border-radius:12px;padding:24px;background:#fffcf5b0;min-width:0}.controls{display:flex;gap:14px;flex-wrap:wrap}.toggle{display:flex;align-items:center;gap:12px;min-width:118px;border:1px solid var(--line);border-radius:9px;padding:14px;background:#faf5e9;cursor:pointer}.toggle input{accent-color:var(--amber);width:20px;height:20px;margin:0}.toggle strong{font-size:18px}.toggle output{font-size:13px;color:var(--muted)}.result{display:flex;align-items:center;gap:18px;margin-bottom:10px}.result>span{color:var(--muted);font-size:14px}.badge{display:inline-flex;padding:3px 19px;border-radius:8px;background:var(--ink);color:#fff8e9;font-size:27px;font-weight:750}.badge.positive{background:var(--amber)}#agreement{font-size:14px;color:#456253;margin:0}.diagram{width:100%;height:auto;display:block;overflow:visible}.diagram .edge{stroke:#bbb8b0;stroke-width:2.5}.diagram .edge.active{stroke:var(--amber);stroke-width:4}.diagram .node rect{fill:#e9e3d5;stroke:#d2c7b0;stroke-width:1.5}.diagram .node text{fill:var(--ink);font-size:17px;font-weight:650}.diagram .node.active rect{fill:var(--active);stroke:var(--amber);stroke-width:2.5}.diagram .node.leaf.active rect{fill:var(--amber)}.diagram .node.leaf.active text{fill:#fffaf1}.diagram .edge-label{fill:#72777e;font-size:13px}.path{display:flex;gap:9px;list-style:none;margin:0;padding:0;flex-wrap:wrap}.path li{background:#f0e4c9;border:1px solid #d7c18d;border-radius:6px;padding:6px 12px;font:14px/1.6 ui-monospace,Consolas,monospace}.path li+li::before{content:'→';margin-right:10px;color:var(--amber)}.path-note{margin-top:22px;font-size:14px;color:var(--muted)}.terms{display:flex;flex-direction:column;gap:10px;margin:0;padding:0;list-style:none}.terms li{border:1px solid var(--line);border-radius:7px;padding:10px 13px;font:14px/1.8 ui-monospace,Consolas,monospace;overflow-wrap:anywhere}.terms li.match{background:var(--active);border-color:var(--amber)}.terms .join{font:12px/1 system-ui,sans-serif;color:var(--muted);margin-left:8px}.minor{font-size:13px;color:var(--muted);margin:16px 0 0}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:center;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}th{font-weight:650;color:var(--muted)}tr.selected{background:#ecdbb3}td button{background:#fffaf0;border:1px solid #c9b689;border-radius:5px;padding:6px 12px;color:var(--ink);font:inherit;cursor:pointer}tr.selected button{background:var(--amber);border-color:var(--amber);color:white}tbody tr{cursor:pointer}button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid #a97422;outline-offset:4px}footer{font-size:12px;color:var(--muted);margin-top:28px;border-top:1px solid var(--line);padding-top:20px}.metadata{font:12px/1.6 ui-monospace,Consolas,monospace;color:var(--muted);margin:15px 0 0}.noscript{padding:16px;border:1px solid var(--amber)}
@media(max-width:700px){main{padding:26px 18px 40px}.grid{grid-template-columns:1fr;gap:16px}.card{padding:19px}h1{font-size:29px}.toggle{min-width:92px;padding:12px;gap:8px}.controls{gap:9px}.toggle output{font-size:12px}th,td{padding:9px 10px}.diagram .node text{font-size:19px}.diagram .edge-label{font-size:15px}}
</style></head>
<body><main><nav><span>__EYEBROW__</span><a id="language-link" href="__COUNTERPARTFILE__">__COUNTERPART__</a></nav>
<h1>__TITLE__</h1><p class="intro">__INTRO__</p><p class="scope">__SCOPE__</p>
<noscript><p class="noscript">__NOSCRIPT__</p></noscript>
<div class="grid"><section class="card"><h2>__INPUTS__</h2><div id="controls" class="controls"></div><p id="metadata" class="metadata"></p></section>
<section class="card" aria-live="polite"><div class="result"><span>__RESULT__</span><strong id="prediction" class="badge"></strong></div><p id="agreement"></p></section></div>
<section class="card"><h2>__TREE__</h2><svg id="tree" class="diagram" viewBox="0 0 760 350" role="img" aria-label="__TREE__"></svg></section>
<div class="grid"><section class="card"><h2>__PATH__</h2><ol id="path" class="path"></ol><p class="path-note" id="path-result"></p></section>
<section class="card"><h2>__LOGIC__</h2><ul id="terms" class="terms"></ul><p id="logic-note" class="minor"></p></section></div>
<section class="card"><h2>__TABLE__</h2><p class="minor" style="margin:0 0 15px">__TABLENOTE__</p><div class="table-wrap"><table id="truth-table"><thead></thead><tbody></tbody></table></div></section>
<footer>__SOURCE__</footer></main>
<script id="model-data" type="application/json">__MODEL__</script>
<script>
'use strict';
const model=JSON.parse(document.getElementById('model-data').textContent);
const words=__WORDS__;
const features=Object.keys(model.training_rows[0]).filter(name=>name!=='target').sort();
const controls=document.getElementById('controls'), table=document.getElementById('truth-table');
const inputState=Object.fromEntries(features.map(name=>[name,false]));
const bool=value=>words[value?'true':'false'];
const nodeMap=new Map(),edgeMap=new Map(),rows=[],terms=[];
const ns='http://www.w3.org/2000/svg';
const svg=document.getElementById('tree');
function element(name,attributes={},text){const item=document.createElementNS(ns,name);for(const[key,value]of Object.entries(attributes))item.setAttribute(key,String(value));if(text!==undefined)item.textContent=text;return item;}
function predictTree(input){let current=model.tree,id='root';const path=[],ids=[id],edges=[];while(!Object.hasOwn(current,'prediction')){const value=input[current.attribute];path.push({attribute:current.attribute,value});id+='/'+String(value);edges.push(id);ids.push(id);current=current.branches[String(value)];}return{prediction:current.prediction,path,ids,edges};}
function predictDNF(input){return model.logic_terms.some(term=>Object.entries(term).every(([name,value])=>input[name]===value));}
function selectRow(index){for(const name of features)inputState[name]=model.training_rows[index][name];update();}
function buildTree(){let leafIndex=0,maxDepth=0;const nodes=[],edges=[];function place(node,id,depth){maxDepth=Math.max(maxDepth,depth);const item={node,id,depth};nodes.push(item);if(Object.hasOwn(node,'prediction'))item.x=leafIndex++;else{const children=Object.entries(node.branches).map(([branch,child])=>{const next=place(child,id+'/'+branch,depth+1);edges.push({from:item,to:next,branch,id:id+'/'+branch});return next;});item.x=children.reduce((sum,child)=>sum+child.x,0)/children.length;}return item;}place(model.tree,'root',0);for(const item of nodes){item.x=85+item.x*(590/Math.max(1,leafIndex-1));item.y=35+item.depth*(270/Math.max(1,maxDepth));}for(const item of edges){const line=element('line',{x1:item.from.x,y1:item.from.y+17,x2:item.to.x,y2:item.to.y-17,class:'edge'});svg.append(line);edgeMap.set(item.id,line);const label=element('text',{x:(item.from.x+item.to.x)/2+8,y:(item.from.y+item.to.y)/2,class:'edge-label'},bool(item.branch==='true'));svg.append(label);}for(const item of nodes){const leaf=Object.hasOwn(item.node,'prediction');const group=element('g',{class:'node'+(leaf?' leaf':''),transform:`translate(${item.x},${item.y})`});group.append(element('rect',{x:-43,y:-19,width:86,height:38,rx:7}));group.append(element('text',{'text-anchor':'middle','dominant-baseline':'middle'},leaf?bool(item.node.prediction):item.node.attribute));svg.append(group);nodeMap.set(item.id,group);}}
for(const name of features){const label=document.createElement('label');label.className='toggle';const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.dataset.feature=name;checkbox.setAttribute('aria-label',name);checkbox.addEventListener('change',()=>{inputState[name]=checkbox.checked;update();});const strong=document.createElement('strong');strong.textContent=name;const output=document.createElement('output');output.dataset.value=name;label.append(checkbox,strong,output);controls.append(label);}
const header=document.createElement('tr');for(const name of[words.selection,...features,words.treeResult,words.logicResult,words.label]){const cell=document.createElement('th');cell.scope='col';cell.textContent=name;header.append(cell);}table.tHead.append(header);
for(const[index,row]of model.training_rows.entries()){const tr=document.createElement('tr');tr.dataset.row=String(index);const first=document.createElement('td');const button=document.createElement('button');button.type='button';button.dataset.row=String(index);button.textContent=features.map(name=>Number(row[name])).join('');button.setAttribute('aria-label',features.map(name=>name+'='+bool(row[name])).join(', '));first.append(button);tr.append(first);for(const value of[...features.map(name=>row[name]),predictTree(row).prediction,predictDNF(row),row.target]){const td=document.createElement('td');td.textContent=bool(value);tr.append(td);}tr.addEventListener('click',()=>selectRow(index));table.tBodies[0].append(tr);rows.push(tr);}
for(const[index,term]of model.logic_terms.entries()){const li=document.createElement('li');if(index){const join=document.createElement('span');join.className='join';join.textContent='OR ';li.append(join);}li.append(document.createTextNode(Object.keys(term).length?Object.entries(term).map(([name,value])=>name+' = '+bool(value)).join(' AND '):bool(true)));document.getElementById('terms').append(li);terms.push(li);}
function update(){for(const checkbox of controls.querySelectorAll('input'))checkbox.checked=inputState[checkbox.dataset.feature];for(const output of controls.querySelectorAll('output'))output.textContent=bool(inputState[output.dataset.value]);const tree=predictTree(inputState),dnf=predictDNF(inputState);const prediction=document.getElementById('prediction');prediction.textContent=bool(tree.prediction);prediction.classList.toggle('positive',tree.prediction);document.getElementById('agreement').textContent=tree.prediction===dnf?words.agreement:words.disagreement;document.getElementById('agreement').dataset.agreement=String(tree.prediction===dnf);const path=document.getElementById('path');path.replaceChildren();for(const step of tree.path){const li=document.createElement('li');li.textContent=step.attribute+' = '+bool(step.value);path.append(li);}document.getElementById('path-result').textContent=words.leaf+' → '+bool(tree.prediction);for(const[id,node]of nodeMap)node.classList.toggle('active',tree.ids.includes(id));for(const[id,edge]of edgeMap)edge.classList.toggle('active',tree.edges.includes(id));let matched=false;for(const[index,term]of model.logic_terms.entries()){const match=Object.entries(term).every(([name,value])=>inputState[name]===value);terms[index].classList.toggle('match',match);matched ||= match;}document.getElementById('logic-note').textContent=matched?words.matching:words.none;for(const[index,row]of model.training_rows.entries()){const selected=features.every(name=>inputState[name]===row[name]);rows[index].classList.toggle('selected',selected);rows[index].querySelector('button').setAttribute('aria-pressed',String(selected));}window.symbolicDemoState={input:{...inputState},tree_prediction:tree.prediction,dnf_prediction:dnf,path:tree.path};}
document.getElementById('metadata').textContent=model.algorithm+' | '+words.nodes+' '+model.complexity.nodes+' | '+words.depth+' '+model.complexity.depth;
if(location.pathname.includes('/demos/symbolic-learning/')){const link=document.getElementById('language-link');link.href='/projects/project-08/';link.textContent=words.return;}
buildTree();update();document.documentElement.dataset.ready='true';
</script></body></html>
'''


def build(model_path: Path, output_dir: Path) -> None:
    model = json.loads(model_path.read_text(encoding="utf-8"))
    if not isinstance(model.get("logic_terms"), list):
        raise ValueError("The exported model requires a logic_terms list.")
    if len(model.get("training_rows", [])) != 8 or not isinstance(model.get("tree"), dict):
        raise ValueError("Expected the exported eight-input explanatory tree.")
    encoded = json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    output_dir.mkdir(parents=True, exist_ok=True)
    for lang, words in WORDS.items():
        page = TEMPLATE.replace("__LANG__", lang).replace("__MODEL__", encoded)
        page = page.replace("__WORDS__", json.dumps(words, ensure_ascii=False))
        for key, value in words.items():
            page = page.replace("__" + key.upper() + "__", value)
        filename = "index.html" if lang == "en" else "index.ko.html"
        (output_dir / filename).write_text(page, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=PROJECT / "examples/explanation.json")
    parser.add_argument("--output", type=Path, default=PROJECT / "demo")
    args = parser.parse_args()
    build(args.model, args.output)
