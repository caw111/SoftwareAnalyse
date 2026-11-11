const fs=require('fs'),path=require('path');
const rt='C:/Users/34267/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {instance}=require(rt+'/@viz-js/viz');
const sharp=require(rt+'/sharp');
(async()=>{
 if(process.argv[2]==='png'){
  const dir=path.join(__dirname,'..','图件');
  for(const name of fs.readdirSync(dir).filter(x=>x.endsWith('.svg'))){
   const data=await sharp(path.join(dir,name),{density:140,limitInputPixels:false}).png().toBuffer();
   const target=path.join(dir,name.replace('.svg','.png'));
   const temporary=path.join(__dirname,'export-'+name.slice(0,7)+'.png');
   fs.writeFileSync(temporary,data);
   fs.renameSync(temporary,target);
   console.log(name);
  }
 }else{
  const viz=await instance();
  for(const file of fs.readdirSync(__dirname).filter(x=>/^diagram-\d+.dot$/.test(x))){
   const dot=fs.readFileSync(path.join(__dirname,file),'utf8');
   const j=viz.renderJSON(dot);fs.writeFileSync(path.join(__dirname,file.replace('diagram','layout').replace('.dot','.json')),JSON.stringify(j));
   console.log(file,j.bb);
  }
 }
})().catch(e=>{console.error(e);process.exit(1)});
