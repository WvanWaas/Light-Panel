(function(root){
 function layout(data,width=600,now=(globalThis.FrameoClock?.now()??Date.now()),options={}){
  const left=39,right=options.right||13,w=Math.max(240,Math.round(width)),top=20,bottom=169;
  const start=Date.parse(data.start),end=Date.parse(data.end),span=end-start;
  const values=(data.points||[]).map(point=>point.price*100).filter(Number.isFinite);
  let min=Math.floor(Math.min(0,...values)/5)*5,max=Math.ceil(Math.max(0,...values)/5)*5;if(max===min)max=min+1;
  const y=value=>bottom-(value-min)/(max-min)*(bottom-top),x=time=>left+(time-start)/span*(w-left-right);
  const points=(data.points||[]).map(point=>{const a=Date.parse(point.start),b=Date.parse(point.end),value=point.price*100;return {...point,value,a,b,x:x(a),width:Math.max(.5,x(b)-x(a)-.6),y:Math.min(y(value),y(0)),height:Math.abs(y(value)-y(0)),current:a<=now&&now<b}});
  return {width:w,height:205,left,right,min,max,baseline:y(0),points,x,y,start,end,nowX:now>=start&&now<end?x(now):null};
 }
 const api={layout};if(typeof module!=='undefined')module.exports=api;else root.PriceChart=api;
})(typeof window!=='undefined'?window:globalThis);
