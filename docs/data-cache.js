(()=>{
  const nativeFetch=window.fetch.bind(window);
  const cache=new Map();
  const RAW='https://raw.githubusercontent.com/tlaw77/fpl/main/data/';
  const normalize=input=>{
    try{
      const raw=typeof input==='string'?input:input?.url||String(input);
      const u=new URL(raw,location.href);
      if(!u.href.startsWith(RAW)) return null;
      u.searchParams.delete('t');
      return u.href;
    }catch{return null}
  };
  async function snapshot(input,init){
    const key=normalize(input);
    if(!key)return nativeFetch(input,init);
    if(!cache.has(key)){
      cache.set(key,(async()=>{
        const r=await nativeFetch(key,{...init,cache:'default'});
        const body=await r.text();
        return {body,status:r.status,statusText:r.statusText,headers:[...r.headers.entries()]};
      })().catch(e=>{cache.delete(key);throw e}));
    }
    const x=await cache.get(key);
    return new Response(x.body,{status:x.status,statusText:x.statusText,headers:x.headers});
  }
  window.fetch=snapshot;
  window.FPLData={
    async json(url){const r=await snapshot(url);if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json()},
    clear(){cache.clear()},
    size(){return cache.size}
  };
})();
