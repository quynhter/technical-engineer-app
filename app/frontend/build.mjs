import {build} from 'esbuild';
import {createElement as h} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {JSDOM} from 'jsdom';
import {writeFile, readFile, access} from 'node:fs/promises';
import {Button, Card, TextInput, TextArea, Badge, Table, Heading} from '@astryxdesign/core';

// Bake the actual library's primitive attributes, not a hand-copied imitation.
// Existing business forms retain their DOM nodes, listeners and native values.
const recipes={};
function bake(key,element,selector){
 const doc=new JSDOM(renderToStaticMarkup(element)).window.document;
 const node=doc.querySelector(selector);
 if(!node)throw Error(`Missing Astryx primitive: ${key}`);
 recipes[key]=Object.fromEntries([...node.attributes].filter(a=>a.name==='class'||a.name==='style'||a.name.startsWith('data-')).map(a=>[a.name,a.value]));
 if(key.startsWith('button-'))recipes[key].content=node.innerHTML;
}
for(const variant of ['primary','secondary','ghost','destructive'])bake('button-'+variant,h(Button,{label:'__ITD_LABEL__',variant,size:'md'}),'button');
bake('card',h(Card,{padding:4},'Content'),'div');
bake('input',h(TextInput,{label:'Field',size:'lg'}),'input');
bake('input-wrapper',h(TextInput,{label:'Field',size:'md',value:''}),'.astryx-text-input');
bake('textarea-wrapper',h(TextArea,{label:'Field',value:''}),'.astryx-text-area');
for(const level of [1,2,3,4])bake('heading-'+level,h(Heading,{level,hasCapsize:false},'Heading'),'h'+level);
bake('textarea',h(TextArea,{label:'Field'}),'textarea');
bake('badge',h(Badge,{label:'Status'}),'span');
const table=h(Table,{data:[{id:1,name:'Item'}],columns:[{key:'name',header:'Name'}],hasHover:true});
for(const [key,sel] of Object.entries({table:'table',thead:'thead',tbody:'tbody',th:'th',td:'td',tr:'tbody tr'}))bake(key,table,sel);
await writeFile('src/primitives.json',JSON.stringify(recipes,null,2)+'\n');
await build({loader:{'.svg':'text','.woff2':'dataurl','.woff':'dataurl'},entryPoints:['src/design.jsx'],bundle:true,minify:true,format:'iife',target:['es2022'],outfile:'../itd/web_assets/design.js',legalComments:'eof',define:{'process.env.NODE_ENV':'"production"'},metafile:true}).then(async result=>{
 await writeFile('bundle-meta.json',JSON.stringify({inputs:Object.keys(result.metafile.inputs).length,outputs:result.metafile.outputs},null,2)+'\n');
});
const license=await readFile('ASTRYX-LICENSE.txt','utf8');
let notices=`Astryx 0.7.15 — https://github.com/meta/astryx\n${license}\n\n`;
for(const name of ['react','react-dom','scheduler','@stylexjs/stylex','styleq','lucide-react','intl-messageformat','@formatjs/fast-memoize','@formatjs/icu-messageformat-parser','@formatjs/icu-skeleton-parser','@formatjs/ecma402-abstract']){
 for(const filename of ['LICENSE','LICENSE.md','LICENSE.txt']){
  try{notices+=`\n\n${name}\n${await readFile(`node_modules/${name}/${filename}`,'utf8')}`;break;}catch(_){}
 }
}
await writeFile('../itd/web_assets/design-LICENSE.txt',notices);
