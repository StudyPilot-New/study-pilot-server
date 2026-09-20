'use strict';
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
if(!reduced && 'IntersectionObserver' in window){
  document.documentElement.classList.add('motion-ready');
  const observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){entry.target.classList.add('visible');observer.unobserve(entry.target);}},{threshold:.08});
  document.querySelectorAll('.reveal').forEach(node=>observer.observe(node));
}
const range=document.getElementById('paceRange'),count=document.getElementById('questionCount');
if(range&&count){const update=()=>{const n=Number(count.value),seconds=Number(range.value);document.getElementById('paceValue').textContent=seconds+' s';document.getElementById('durationValue').textContent=Number.isInteger(n)&&n>=1&&n<=1000?Math.round(seconds*n/60):'—';const preview=document.getElementById('previewSeconds');preview.replaceChildren(document.createTextNode(seconds),Object.assign(document.createElement('span'),{textContent:'s'}));};range.addEventListener('input',update);count.addEventListener('input',update);update();}
