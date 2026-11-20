/* Two DOM image layers; preload into the inactive layer, never blank a good photo. */
(function(root){
 class PhotoFrame {
  constructor(element,options={}){
   this.element=element;this.interval=options.interval||15000;this.fade=options.fade??1500;
   this.onStatus=options.onStatus||function(){};this.urls=[];this.current=-1;this.index=-1;
   this.ready=false;this.loading=false;this.fading=false;this.paused=false;this.wanted=false;this.failures=0;this.generation=0;
   this.layers=[0,1].map(()=>{const img=document.createElement('img');img.className='photo-layer';img.alt='';img.setAttribute('aria-hidden','true');img.decoding='async';element.appendChild(img);return img});
   this.visibility=()=>this.pause(document.hidden||document.body.classList.contains('panel-open'));
   document.addEventListener('visibilitychange',this.visibility);
  }
  setPhotos(urls){
   clearTimeout(this.timer);clearTimeout(this.fadeTimer);this.generation++;
   this.urls=[...new Set(urls.filter(url=>typeof url==='string'&&url))];
   this.current=-1;this.index=-1;this.ready=false;this.loading=false;this.fading=false;this.wanted=false;this.failures=0;
   for(const image of this.layers){image.onload=null;image.onerror=null;image.removeAttribute('src');image.className='photo-layer'}
   this.onStatus(this.urls.length?'loading':'empty');
   if(this.urls.length)this.preload();
  }
  preload(){
   if(this.loading||this.ready||this.fading||!this.urls.length||this.failures>=this.urls.length)return;
   const slot=this.current===0?1:0,img=this.layers[slot],generation=this.generation;
   this.index=(this.index+1)%this.urls.length;this.loading=true;img.className='photo-layer';
   img.onload=()=>{if(generation!==this.generation)return;this.loading=false;this.ready=true;this.failures=0;img.onload=null;img.onerror=null;if(this.current<0||this.wanted)this.next()};
   img.onerror=()=>{if(generation!==this.generation)return;this.loading=false;this.failures++;img.onload=null;img.onerror=null;
    if(this.failures>=this.urls.length){this.onStatus(this.current<0?'error':'visible');this.wanted=false;return}this.preload()};
   img.src=this.urls[this.index];
  }
  next(){
   if(this.paused||document.hidden||this.fading||!this.urls.length)return;
   clearTimeout(this.timer);
   if(!this.ready){this.wanted=true;if(this.failures>=this.urls.length)this.failures=0;this.preload();return}
   this.wanted=false;const previous=this.current,next=previous===0?1:0;
   this.current=next;this.ready=false;this.onStatus('visible');
   // Flush the inactive starting transform before starting opacity/zoom on this layer.
   void this.layers[next].offsetWidth;
   this.layers[next].classList.add('is-visible','is-moving');
   if(previous>=0)this.layers[previous].classList.remove('is-visible');
   this.fading=true;
   this.fadeTimer=setTimeout(()=>{this.fading=false;if(previous>=0)this.layers[previous].className='photo-layer';
    if(this.urls.length>1){this.preload();this.schedule(previous<0?this.interval:this.interval-this.fade)}
   },previous<0?0:this.fade);
  }
  schedule(delay=this.interval){clearTimeout(this.timer);if(!this.paused&&this.urls.length>1)this.timer=setTimeout(()=>this.next(),Math.max(100,delay))}
  pause(value){this.paused=Boolean(value);this.element.classList.toggle('photo-paused',this.paused);if(this.paused)clearTimeout(this.timer);else if(this.current<0&&this.ready)this.next();else this.schedule()}
 }
 root.PhotoFrame=PhotoFrame;
})(window);
