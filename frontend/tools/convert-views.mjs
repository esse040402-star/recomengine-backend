import fs from 'node:fs';
import {parse,parseExpression} from '@babel/parser';
import traverse from '@babel/traverse';
import generate from '@babel/generator';
import * as t from '@babel/types';
import {parseDocument} from 'htmlparser2';
const groups={
 'pages/WelcomePage':['welcome'], 'pages/HomePage':['home'], 'pages/ResultPage':['quickResult'], 'pages/DeepIntroPage':['deepIntro'], 'pages/SurveyPage':['survey'],
 'pages/ExplorePage':['exploreScreen','exploreResults','exploreGames'],
 'pages/RankingsPage':['rankings','globalRankRow','rankGenreControls','filteredGlobalRanks','matchesRankCategories','matchesRankPlatform','matchesRankGenre'],
 'pages/NewsPage':['newsScreen','marketCard'], 'pages/SavedPage':['savedGames'],
 'pages/ProfilePage':['profile','playerProfileHub','activityPanel','profileSettings','accountSettings','accountLinks'],
 'pages/ReportPage':['reportScreen','axisBars'],
 'pages/GameDetailPage':['gamePage','gameSection','gameRequirements','gameReviews','gameGallery','gameMedia','gameFit','gameEvidence','steamOverview','steamInfo'],
 'components/game/GameCard':['card','steamBadge','noMatches'],
 'components/game/Reviews':['reviewsScreen','steamReviewSummary','reviewBrowser','filteredReviews','steamReviewCard','marketStamp'],
 'components/recommendation/RecommendationChat':['recommendationChat','guidedChatBody'],
 'components/game/HeroSlide':['heroSlide'],
 'components/common/DialogContents':['restartDialog','filtersDialog','customizeBody','profileEditorBody','reviewForm','answersDialog','retake','feedbackDialog','accountDialog'],
};
const allNames=Object.values(groups).flat(),functions={};
for(const file of ['app.js','game-pages.js','market-ui.js','steam-ui.js','personalization.js','team-feedback.js'])for(const n of parse(fs.readFileSync('../project/integrated/'+file,'utf8')).program.body){if(n.type==='FunctionDeclaration'&&allNames.includes(n.id.name))functions[n.id.name]=n;if(n.type==='VariableDeclaration')for(const d of n.declarations)if(allNames.includes(d.id.name)&&d.init?.type==='ArrowFunctionExpression')functions[d.id.name]=t.functionDeclaration(d.id,d.init.params,t.isBlockStatement(d.init.body)?d.init.body:t.blockStatement([t.returnStatement(d.init.body)]));}
const markupNames=new Set(allNames.filter(x=>!['gameMedia','gameFit','exploreGames','filteredReviews','filteredGlobalRanks','matchesRankCategories','matchesRankPlatform','matchesRankGenre'].includes(x)).concat(['icon','btn','routeBtn','link','heroCarousel','selectField']));
const frag=children=>t.jsxFragment(t.jsxOpeningFragment(),t.jsxClosingFragment(),children.map(x=>t.isJSXElement(x)||t.isJSXFragment(x)?x:t.jsxExpressionContainer(x)));
const isMarkup=x=>t.isJSXElement(x)||t.isJSXFragment(x)||(t.isCallExpression(x)&&t.isIdentifier(x.callee)&&markupNames.has(x.callee.name))||(t.isConditionalExpression(x)&&(isMarkup(x.consequent)||isMarkup(x.alternate)))||(t.isBinaryExpression(x)&&x.operator==='+'&&(isMarkup(x.left)||isMarkup(x.right)));
let count=0;
function convertHTML(str,expressions=[]){const my=++count,marker=i=>`zzexpr${my}n${i}zz`;let html=Array.isArray(str)?str.map((q,i)=>q+(i<expressions.length?marker(i):'')).join(''):str;const rx=new RegExp(`zzexpr${my}n(\\d+)zz`,'g');
 const interp=(text,attr=false)=>{const parts=[];let last=0;for(const m of text.matchAll(rx)){if(m.index>last)parts.push(t.stringLiteral(text.slice(last,m.index)));parts.push(expressions[+m[1]]);last=m.index+m[0].length;}if(last<text.length)parts.push(t.stringLiteral(text.slice(last)));if(!parts.length)return t.stringLiteral('');if(parts.length===1)return parts[0];return attr?parts.reduce((a,b)=>t.binaryExpression('+',a,b)):frag(parts);};
 const propName=n=>({class:'className',for:'htmlFor',tabindex:'tabIndex',maxlength:'maxLength',minlength:'minLength',autocomplete:'autoComplete',datetime:'dateTime',readonly:'readOnly',autofocus:'autoFocus',viewbox:'viewBox','stroke-width':'strokeWidth','stroke-linecap':'strokeLinecap','stroke-linejoin':'strokeLinejoin'})[n]||n;
 const convert=n=>{if(n.type==='text')return n.data?interp(n.data):null;if(n.type!=='tag')return null;let tag=({button:'ActionButton',img:'GameImage',input:'Field',textarea:'FieldArea',form:'Form',select:'Select',a:'Anchor'})[n.name]||n.name;const attrs=[];
 for(const [name,value]of Object.entries(n.attribs||{})){if(name.startsWith(`zzexpr${my}`)){const i=+name.match(/n(\d+)zz/)[1];attrs.push(t.jsxSpreadAttribute(t.callExpression(t.memberExpression(t.identifier('ctx'),t.identifier('attrs')),[expressions[i]])));continue;}let pn=propName(name),v=interp(value,true);if(name==='style')v=t.callExpression(t.memberExpression(t.identifier('ctx'),t.identifier('style')),[v]);if(['required','disabled','checked','selected','open','multiple','hidden'].includes(name)){v=t.booleanLiteral(true);if(name==='checked')pn='defaultChecked';}if(pn==='selected')continue;attrs.push(t.jsxAttribute(t.jsxIdentifier(pn),t.jsxExpressionContainer(v)));}
 if(n.name==='details')attrs.push(t.jsxAttribute(t.jsxIdentifier('ref'),t.jsxExpressionContainer(t.memberExpression(t.identifier('ctx'),t.identifier('detailsRef')))));
 const children=(n.children||[]).map(convert).filter(Boolean).map(x=>t.isJSXElement(x)||t.isJSXFragment(x)?x:t.jsxExpressionContainer(x));return t.jsxElement(t.jsxOpeningElement(t.jsxIdentifier(tag),attrs,children.length===0),children.length?t.jsxClosingElement(t.jsxIdentifier(tag)):null,children);};
 const nodes=parseDocument(html,{decodeEntities:true}).children.map(convert).filter(Boolean);return nodes.length===1?nodes[0]:frag(nodes);
}
const freeAll=new Set();
for(const [dest,names] of Object.entries(groups)){
 const ast=t.file(t.program(names.map(name=>{if(!functions[name])throw Error(name);return t.cloneNode(functions[name],true)})));
 traverse(ast,{StringLiteral:{exit(p){if(/^\s*<[a-z]/i.test(p.node.value)){p.replaceWith(convertHTML(p.node.value));p.skip();}}},TemplateLiteral:{exit(p){if(p.node.quasis.some(q=>/<[a-z]/i.test(q.value.cooked)) || (p.node.quasis.every(q=>q.value.cooked==='')&&p.node.expressions.some(isMarkup))){p.replaceWith(convertHTML(p.node.quasis.map(q=>q.value.cooked),p.node.expressions));p.skip();}}},BinaryExpression:{exit(p){if(p.node.operator==='+'&&(isMarkup(p.node.left)||isMarkup(p.node.right))){p.replaceWith(frag([p.node.left,p.node.right]));p.skip();}}},CallExpression:{exit(p){if(t.isMemberExpression(p.node.callee)&&p.node.callee.property.name==='join'&&p.node.arguments[0]?.value===''){p.replaceWith(t.callExpression(t.memberExpression(t.memberExpression(t.identifier('React'),t.identifier('Children')),t.identifier('toArray')),[p.node.callee.object]));p.skip();}if(t.isMemberExpression(p.node.callee)&&p.node.callee.property.name==='join'&&p.node.arguments[0]?.value==='<br>그리고 '){p.replaceWith(parseExpression("r.top.map((i,j)=><React.Fragment key={i}>{j>0&&<><br/>그리고 </>}{ctx.E.AXES[i]}</React.Fragment>)",{plugins:['jsx']}));p.skip();}}}});
 const allowed=new Set(['React','Object','Array','String','Number','Boolean','Math','Date','Map','Set','URL','Intl','Infinity','undefined','JSON','structuredClone','console','ctx']);
 for(const node of ast.program.body)node.params.unshift(t.identifier('ctx'));
 traverse(ast,{ReferencedIdentifier(p){if(p.isJSXIdentifier())return;const name=p.node.name;if(allowed.has(name)||p.scope.hasBinding(name))return;freeAll.add(name);p.replaceWith(t.memberExpression(t.identifier('ctx'),t.identifier(name)));},CallExpression(p){if(t.isIdentifier(p.node.callee)&&names.includes(p.node.callee.name))p.node.arguments.unshift(t.identifier('ctx'));}});
 const out="import React from 'react';\nimport {ActionButton,GameImage,Field,FieldArea,Form,Select,Anchor} from '"+(dest.startsWith('pages/')?'../':'../../')+"components/common/Elements.jsx';\n"+ast.program.body.map(n=>'export '+generate(n).code).join('\n\n')+'\n';fs.mkdirSync('src/'+dest.split('/').slice(0,-1).join('/'),{recursive:true});fs.writeFileSync('src/'+dest+'.jsx',out);
}
fs.writeFileSync('src/pages/viewRegistry.js',Object.keys(groups).map((d,i)=>`import * as v${i} from '../${d}.jsx';`).join('\n')+'\nexport const views={'+Object.keys(groups).map((_,i)=>'...v'+i).join(',')+'};\n');
fs.writeFileSync('../tmp/react-reference/free-bindings.json',JSON.stringify([...freeAll].sort(),null,2));console.log('Converted',allNames.length,'functions; free bindings:',[...freeAll].sort().join(', '));
