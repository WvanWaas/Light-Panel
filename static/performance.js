/* Select before CSS paints: Android defaults to lite; ?lite=0 keeps full effects. */
(function(){
  var choice=new URLSearchParams(location.search).get('lite');
  var lite=choice==='1'||(choice!=='0'&&/Android/i.test(navigator.userAgent));
  var motion=new URLSearchParams(location.search).get('motion')!=='0'&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.FrameoPerformance={lite:lite,motion:motion};
  document.documentElement.dataset.motion=motion?'on':'off';
  document.documentElement.dataset.performance=lite?'lite':'full';
})();
