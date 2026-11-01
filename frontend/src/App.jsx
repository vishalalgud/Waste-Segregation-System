import React, { useEffect, useState } from 'react';
import { Camera, Activity, Cpu, Trash2 } from 'lucide-react';

function App() {
  const [image, setImage] = useState(null);
  const [data, setData] = useState({ 
    category: "SYSTEM INITIALIZING...", 
    color: "gray", 
    action: "Waiting for video feed...",
    device: "CHECKING HARDWARE..."
  });

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/video");
    
    ws.onmessage = (event) => {
      const packet = JSON.parse(event.data);
      setImage(packet.image);
      setData(packet.data);
    };

    return () => ws.close();
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 text-white font-mono p-6">
      {/* HEADER */}
      <div className="flex justify-between items-center border-b border-slate-700 pb-4 mb-6">
        <h1 className="text-3xl font-bold text-green-500 flex items-center gap-3">
          <Activity /> ECO-SORT SYSTEM 
          <span className="text-xs text-black bg-green-500 px-2 py-1 rounded font-bold">LIVE V.1.0</span>
        </h1>
        <div className="flex gap-4 text-xs text-gray-400">
           <div className="flex items-center gap-2"><Cpu size={14}/> {data.device || "CPU MODE"}</div>
           <div className="flex items-center gap-2 text-green-400"><Camera size={14}/> CAMERA ACTIVE</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* VIDEO FEED */}
        <div className="lg:col-span-2 relative bg-black rounded-xl overflow-hidden border-2 border-slate-700 shadow-[0_0_30px_rgba(0,0,0,0.5)]">
          {image ? (
            <img src={image} className="w-full h-full object-contain" alt="Live Stream" />
          ) : (
            <div className="h-96 flex items-center justify-center text-slate-500 animate-pulse">
              ESTABLISHING SECURE CONNECTION...
            </div>
          )}
        </div>

        {/* INFO PANEL */}
        <div className="space-y-6">
          <div className="bg-slate-800/50 p-8 rounded-xl border border-slate-600 shadow-xl transition-all duration-300"
               style={{ borderColor: data.color, boxShadow: `0 0 20px ${data.color}20` }}>
            
            <h2 className="text-gray-400 text-xs tracking-[0.2em] mb-2">DETECTED OBJECT</h2>
            <div className="text-5xl font-black mb-4 transition-colors duration-300" style={{ color: data.color }}>
              {data.category}
            </div>
            
            <div className="text-xl text-white font-light border-l-4 pl-4 py-2 bg-slate-800 rounded-r" style={{ borderColor: data.color }}>
              {data.action}
            </div>

            {data.conf > 0 && (
              <div className="mt-6 flex justify-between items-end">
                <div className="text-xs text-gray-500">CONFIDENCE</div>
                <div className="text-2xl font-bold text-slate-300">{(data.conf * 100).toFixed(1)}%</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;