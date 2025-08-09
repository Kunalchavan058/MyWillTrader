import { startCountdown } from "./countdown.js";

export function connectWS({ onState }){
  const proto = location.protocol==="https:"?"wss":"ws";
  let ws;

  function open(){
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onmessage = (e)=>{
      const t = e.data;
      const m = /Time to next\s+(\d+)-min candle:\s+(\d+)s/i.exec(t);
      if(m && m[2]) startCountdown(parseInt(m[2],10));
      try{
        const obj = JSON.parse(t);
        if(obj && obj.type==="state"){ onState?.(obj); return; }
      }catch{}
    };
    ws.onclose = ()=> setTimeout(open, 2000);
  }
  open();
  return () => { try{ ws?.close(); }catch{} };
}
