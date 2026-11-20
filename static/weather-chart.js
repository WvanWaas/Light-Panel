/* Real timestamps share one axis. Hour, symbol and values use fixed aligned rows. */
(function(root){
 const number=value=>value===null||value===undefined||String(value).trim()===''?null:Number.isFinite(Number(value))?Number(value):null;
 function layout(rows,width=600){
  const hour=3600000;
  const points=rows.filter(row=>Number.isFinite(Date.parse(row.datetime))).map(row=>({row,time:Date.parse(row.datetime),temperature:number(row.temperature),rain:number(row.precipitation)})).sort((a,b)=>a.time-b.time).filter((point,index,all)=>index===0||point.time!==all[index-1].time).slice(0,24);
  const w=Math.max(240,Math.round(width)),left=30,right=14,plot=w-left-right;
  const temperatures=points.map(p=>p.temperature).filter(v=>v!==null),minimum=temperatures.length?Math.floor(Math.min(...temperatures))-1:0,maximum=temperatures.length?Math.ceil(Math.max(...temperatures))+1:1;
  const rainMax=Math.max(1,...points.map(p=>p.rain===null?0:Math.max(0,p.rain)));
  const first=points[0]?.time??0,last=points[points.length-1]?.time??first,domainStart=first-hour/2,domainSize=Math.max(hour,last-first+hour);
  const x=time=>left+(time-domainStart)/domainSize*plot;
  const temperatureTop=80,temperatureBottom=144,rainBottom=185,rainHeight=25;
  for(const p of points){if(p.rain!==null&&p.rain<0)p.rain=null;p.x=x(p.time);p.y=p.temperature===null?null:temperatureBottom-(p.temperature-minimum)/(maximum-minimum)*(temperatureBottom-temperatureTop);p.rainHeight=p.rain===null?null:p.rain/rainMax*rainHeight}
  const tickHours=w<440?4:3,samples=[];
  if(points.length)for(let time=first;time<=last;time+=tickHours*hour){const point=points.find(p=>p.time===time);samples.push({time,x:x(time),point:point||null})}
  return {width:w,height:210,left,right,plot,points,samples,tickHours,temperatureTop,temperatureBottom,rainBottom,minimum,maximum,rainMax,hasTemperatures:temperatures.length>0,barWidth:Math.max(2,Math.min(15,plot/Math.max(1,(last-first)/hour+1)*.58))};
 }
 const api={layout};if(typeof module!=='undefined')module.exports=api;else root.WeatherChart=api;
})(typeof window!=='undefined'?window:globalThis);
