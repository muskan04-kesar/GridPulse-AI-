import React, { useState, useEffect, useMemo } from 'react';
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, 
  Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { 
  Zap, Map as MapIcon, ShieldAlert,
  Activity, Clock, ChevronRight, User, Bot,
  ShieldCheck, AlertTriangle, TrendingUp, IndianRupee
} from 'lucide-react';

const COLORS = {
  teal: '#1D9E75',
  tealLt: '#E1F5EE',
  tealDk: '#085041',
  amber: '#BA7517',
  amberLt: '#FAEEDA',
  red: '#E24B4A',
  redLt: '#FCEBEB',
  blue: '#378ADD',
  blueLt: '#E6F1FB',
  bg: '#F8FAFC',
};

const METRICS = [
  { label: 'Active faults', value: '2', color: COLORS.red, delta: '+1 from last hour' },
  { label: 'Grid health', value: '87.5%', color: COLORS.amber, delta: '-2.4% vs yesterday' },
  { label: 'Avg resolve time', value: '38 min', color: COLORS.amber, delta: 'Infrastructure target: 30m' },
  { label: 'Uptime today', value: '94.2%', color: COLORS.teal, delta: 'Above target (92%)' },
];

const TRANSFORMERS = [
  { id: 'T-01', name: 'Civil Lines West', x: 15, y: 15, status: 'ok' },
  { id: 'T-07', name: 'Civil Lines Substation', x: 28, y: 35, status: 'fault' },
  { id: 'T-12', name: 'Katra Crossing', x: 50, y: 15, status: 'warn' },
  { id: 'T-03', name: 'MG Road Primary', x: 82, y: 28, status: 'ok' },
  { id: 'T-09', name: 'High Court Zone', x: 20, y: 65, status: 'ok' },
  { id: 'T-04', name: 'University Block', x: 45, y: 82, status: 'ok' },
  { id: 'T-05', name: 'Rail Overbridge', x: 88, y: 15, status: 'ok' },
  { id: 'T-11', name: 'Lowther Road', x: 92, y: 55, status: 'ok' },
  { id: 'T-08', name: 'Collectorate Gate', x: 35, y: 88, status: 'ok' },
  { id: 'T-10', name: 'Nainital Bank Sq.', x: 72, y: 85, status: 'ok' },
  { id: 'T-06', name: 'Stanley Rd. Jct', x: 55, y: 55, status: 'ok' },
];

const CONNECTIONS = [
  { from: 'T-01', to: 'T-07' }, { from: 'T-07', to: 'T-12' }, { from: 'T-12', to: 'T-03' },
  { from: 'T-03', to: 'T-05' }, { from: 'T-05', to: 'T-11' }, { from: 'T-11', to: 'T-10' },
  { from: 'T-10', to: 'T-04' }, { from: 'T-04', to: 'T-08' }, { from: 'T-08', to: 'T-09' },
  { from: 'T-09', to: 'T-01' }, { from: 'T-07', to: 'T-06' }, { from: 'T-06', to: 'T-03' },
];

const VOLTAGE_DATA = Array.from({ length: 40 }, (_, i) => ({
  time: i,
  voltage: i < 30 ? 220 + Math.random() * 10 : 170 + Math.random() * 15,
}));

const FAULT_COUNTS = [
  { day: 'Mon', count: 1 }, { day: 'Tue', count: 2 }, { day: 'Wed', count: 0 },
  { day: 'Thu', count: 1 }, { day: 'Fri', count: 2 }, { day: 'Sat', count: 0 },
  { day: 'Sun', count: 1 },
];

const FAULT_LOG = [
  { id: 'F-101', target: 'T-07', severity: 'Critical', status: 'dispatched', time: '12:04' },
  { id: 'F-104', target: 'T-12', severity: 'Warning', status: 'monitoring', time: '13:15' },
  { id: 'F-201', target: 'T-03', severity: 'Resolved', status: 'closed', time: '09:30' },
  { id: 'F-198', target: 'T-01', severity: 'Resolved', status: 'closed', time: '08:45' },
  { id: 'F-195', target: 'T-09', severity: 'Resolved', status: 'closed', time: '07:20' },
];

const AGENTS = [
  { id: 'A-W', name: 'Watcher', role: 'Active', type: 'red', avatar: 'W' },
  { id: 'A-A', name: 'Analyst', role: 'Busy — verifying T-12', type: 'blue', avatar: 'A' },
];

const TECHNICIANS = [
  { name: 'Rajesh Kumar', status: 'en route', info: 'ETA 11 min' },
  { name: 'Pradeep Verma', status: 'available', info: 'Stationed at Zone 4' },
];

const GridPulseDashboard = () => {
  const [selectedFaultId, setSelectedFaultId] = useState('F-101');
  const [activeTab, setActiveTab] = useState('Overview');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [uptimeSeconds, setUptimeSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    const uptime = setInterval(() => setUptimeSeconds(s => s + 1), 1000);
    return () => { clearInterval(timer); clearInterval(uptime); };
  }, []);

  const formatUptime = (s) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  const activeTransformer = useMemo(() => {
    const fault = FAULT_LOG.find(f => f.id === selectedFaultId);
    return TRANSFORMERS.find(t => t.id === fault?.target);
  }, [selectedFaultId]);

  return (
    <div className="flex flex-col min-h-screen bg-[#F8FAFC] font-sans selection:bg-teal-light">
      <style>{`
        @keyframes pulse-live { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        @keyframes blink-ring { 0% { transform: scale(0.8); opacity: 1; } 100% { transform: scale(1.8); opacity: 0; } }
        @keyframes edge-flash { 0% { opacity: 1; stroke-width: 4; } 50% { opacity: 0.3; stroke-width: 2; } 100% { opacity: 1; stroke-width: 4; } }
        .animate-pulse-live { animation: pulse-live 1.5s infinite; }
        .animate-blink-ring { animation: blink-ring 1s infinite; }
        .animate-edge-flash { animation: edge-flash 0.8s infinite; }
      `}</style>

      {/* Topbar */}
      <header className="h-16 px-6 bg-white border-b border-gray-100 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-teal flex items-center justify-center">
            <Zap className="text-white w-6 h-6 fill-white" />
          </div>
          <div>
            <h1 className="font-mono font-bold text-xl tracking-tight">Grid<span className="text-teal">Pulse</span> AI</h1>
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mt-0.5">Prayagraj — Zone 4 / Civil Lines</p>
          </div>
        </div>
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2 px-3 py-1 bg-teal-light rounded-full border border-teal/10">
            <div className="w-2 h-2 rounded-full bg-teal animate-pulse-live" />
            <span className="text-[10px] font-bold text-teal uppercase tracking-wider">Live System Active</span>
          </div>
          <div className="font-mono text-sm font-bold text-gray-500 bg-gray-50 px-4 py-1.5 rounded-lg border border-gray-100">
            <Clock className="w-4 h-4 inline-block mr-2 -mt-0.5" />
            {currentTime.toLocaleTimeString('en-US', { hour12: false })}
          </div>
        </div>
      </header>

      {/* Nav tabs */}
      <nav className="h-14 px-6 bg-white border-b border-gray-100 flex items-center gap-10">
        {['Overview', 'Fault log', 'Agents', 'Analytics', 'Technicians', 'Settings'].map(tab => (
          <button 
            key={tab} 
            onClick={() => setActiveTab(tab)}
            className={`h-full relative px-2 text-[11px] font-bold uppercase tracking-[0.2em] transition-all
              ${activeTab === tab ? 'text-teal' : 'text-gray-400 hover:text-gray-600'}`}
          >
            {tab}
            {activeTab === tab && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-teal" />}
          </button>
        ))}
      </nav>

      <main className="flex-1 p-6 space-y-6 overflow-y-auto">
        {/* Metric Cards */}
        <div className="grid grid-cols-4 gap-6">
          {METRICS.map((m, i) => (
            <div key={i} className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow cursor-default">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">{m.label}</p>
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-3xl font-bold tracking-tighter" style={{ color: m.color }}>{m.value}</span>
              </div>
              <p className="mt-2 text-[10px] font-medium text-gray-400 border-t border-gray-50 pt-2">{m.delta}</p>
            </div>
          ))}
        </div>

        {/* Main Body */}
        <div className="flex gap-6 h-[640px]">
          {/* Left Panel */}
          <div className="flex-1 flex flex-col gap-6 min-w-0">
            {/* Transformer Grid */}
            <div className="flex-[3] bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden flex flex-col">
              <div className="px-6 py-4 border-b border-gray-50 flex justify-between items-center bg-gray-50/30">
                <div className="flex items-center gap-2">
                  <MapIcon className="w-4 h-4 text-teal" />
                  <h2 className="text-[11px] font-bold text-gray-600 uppercase tracking-widest">Network Topology — Zone 4</h2>
                </div>
                <div className="flex gap-4">
                  <div className="flex items-center gap-2 text-[9px] font-bold text-gray-400 uppercase tracking-widest leading-none">
                    <div className="w-2 h-2 rounded-full bg-teal" /> OK
                  </div>
                  <div className="flex items-center gap-2 text-[9px] font-bold text-gray-400 uppercase tracking-widest leading-none">
                    <div className="w-2 h-2 rounded-full bg-amber" /> WARN
                  </div>
                  <div className="flex items-center gap-2 text-[9px] font-bold text-gray-400 uppercase tracking-widest leading-none">
                    <div className="w-2 h-2 rounded-full bg-red" /> FAULT
                  </div>
                </div>
              </div>
              <div className="flex-1 relative bg-[#FDFDFD] p-10 cursor-crosshair overflow-hidden">
                <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#1D9E75 2px, transparent 0)', backgroundSize: '40px 40px' }} />
                
                {/* SVG Connections */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
                  {CONNECTIONS.map((c, i) => {
                    const start = TRANSFORMERS.find(t => t.id === c.from);
                    const end = TRANSFORMERS.find(t => t.id === c.to);
                    if (!start || !end) return null;
                    const isFaultyPath = (activeTransformer?.id === start.id || activeTransformer?.id === end.id) && (start.status !== 'ok' || end.status !== 'ok');
                    
                    return (
                      <line 
                        key={i} 
                        x1={`${start.x}%`} y1={`${start.y}%`} 
                        x2={`${end.x}%`} y2={`${end.y}%`} 
                        stroke={isFaultyPath ? COLORS.red : '#E2E8F0'} 
                        strokeWidth={isFaultyPath ? "3" : "1.5"} 
                        className={isFaultyPath ? 'animate-edge-flash' : ''}
                      />
                    );
                  })}
                </svg>

                {/* Transformer Dots */}
                {TRANSFORMERS.map(t => (
                  <div 
                    key={t.id} 
                    className="absolute group z-10 transition-transform hover:scale-125"
                    style={{ left: `${t.x}%`, top: `${t.y}%`, transform: 'translate(-50%, -50%)' }}
                  >
                    <div className="relative flex items-center justify-center">
                      <div className={`w-5 h-5 rounded-full border-2 border-white shadow-lg relative z-10 
                        ${t.status === 'fault' ? 'bg-red' : t.status === 'warn' ? 'bg-amber' : 'bg-teal'}`} 
                      />
                      {t.status === 'fault' && (
                        <div className="absolute w-10 h-10 rounded-full border-2 border-red opacity-0 animate-blink-ring" />
                      )}
                      
                      {/* Tooltip */}
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 bg-gray-900 text-white text-[9px] px-2.5 py-1.5 rounded-lg whitespace-nowrap hidden group-hover:block z-20 font-bold shadow-xl">
                        <p>{t.name}</p>
                        <p className="text-gray-400 font-mono mt-0.5">{t.id} | Status: {t.status.toUpperCase()}</p>
                        <div className="absolute top-full left-1/2 -translate-x-1/2 border-x-[6px] border-x-transparent border-t-[6px] border-t-gray-900" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Charts Row */}
            <div className="flex-[2] grid grid-cols-2 gap-6 min-h-0">
              <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6 flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Real-time Voltage — T-07</h3>
                  <div className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-red animate-pulse" /><span className="text-[9px] font-bold text-red">Unstable Signal</span></div>
                </div>
                <div className="flex-1 w-full min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={VOLTAGE_DATA}>
                      <Line 
                        type="monotone" 
                        dataKey="voltage" 
                        stroke={COLORS.teal} 
                        strokeWidth={2} 
                        dot={(props) => {
                          const { cx, cy, payload } = props;
                          if (payload.time >= 30) return <circle cx={cx} cy={cy} r={2} fill={COLORS.red} />;
                          return null;
                        }}
                      />
                      <XAxis hide />
                      <YAxis hide domain={['dataMin - 10', 'dataMax + 10']} />
                      <Tooltip 
                        contentStyle={{ fontSize: '10px', borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                        labelStyle={{ display: 'none' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6 flex flex-col">
                <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-4">Daily Fault Distribution</h3>
                <div className="flex-1 w-full min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={FAULT_COUNTS}>
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {FAULT_COUNTS.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.count >= 2 ? COLORS.red : COLORS.teal} />
                        ))}
                      </Bar>
                      <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#94A3B8', fontWeight: 600 }} />
                      <Tooltip 
                        cursor={{ fill: '#F1F5F9' }}
                        contentStyle={{ fontSize: '10px', borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar */}
          <aside className="w-[248px] flex flex-col gap-6 shrink-0 h-full">
            {/* Fault Log */}
            <div className="flex-[3] bg-white rounded-3xl border border-gray-100 shadow-sm flex flex-col min-h-0">
              <div className="px-5 py-4 border-b border-gray-50 flex justify-between items-center">
                <h2 className="text-[11px] font-bold text-gray-600 uppercase tracking-widest">Active Logs</h2>
                <span className="text-[10px] font-mono font-bold text-gray-400">Total: 5</span>
              </div>
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
                {FAULT_LOG.map(f => (
                  <button 
                    key={f.id} 
                    onClick={() => setSelectedFaultId(f.id)}
                    className={`w-full text-left p-3 rounded-2xl transition-all border
                      ${selectedFaultId === f.id ? 'bg-teal-light border-teal/20' : 'bg-white border-transparent hover:bg-gray-50'}`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className={`text-[9px] font-bold uppercase tracking-widest ${f.severity === 'Critical' ? 'text-red' : f.severity === 'Warning' ? 'text-amber' : 'text-teal'}`}>
                        {f.severity}
                      </span>
                      <span className="text-[9px] font-mono text-gray-400">{f.time}</span>
                    </div>
                    <p className="text-xs font-bold text-gray-700">{f.target} Sub-Unit</p>
                    <p className="text-[10px] text-gray-500 mt-1 capitalize">{f.status}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* AI Agents & Technicians */}
            <div className="flex-[2] bg-[#0F172A] rounded-3xl p-5 shadow-inner flex flex-col gap-4">
              <h2 className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-1">AI Agents on Duty</h2>
              <div className="space-y-4">
                {AGENTS.map(a => (
                  <div key={a.id} className="flex gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white shadow-lg ${a.type === 'red' ? 'bg-red' : 'bg-blue'}`}>
                      {a.avatar}
                    </div>
                    <div className="min-w-0">
                      <p className="text-[11px] font-bold text-white leading-none mb-1">{a.name}</p>
                      <p className={`text-[9px] font-bold capitalize ${a.type === 'red' ? 'text-teal-400' : 'text-blue-400'}`}>
                        {a.role}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="h-px bg-slate-800 my-1" />
              <div className="space-y-4 overflow-y-auto pr-1">
                {TECHNICIANS.map((t, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                      <User className="w-4 h-4 text-slate-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-[11px] font-bold text-slate-200 leading-none mb-1">{t.name}</p>
                      <p className="text-[9px] text-slate-500 font-medium capitalize">{t.status} — {t.info}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>

      {/* Footer */}
      <footer className="h-16 px-6 bg-white border-t border-gray-100 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-10">
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest">Transformers tracked</span>
            <span className="text-xs font-mono font-bold text-gray-700">11</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest">Agents online</span>
            <span className="text-xs font-mono font-bold text-gray-700">2</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest">On shift</span>
            <span className="text-xs font-mono font-bold text-gray-700">4</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest">Session Uptime</span>
            <span className="text-xs font-mono font-bold text-teal">{formatUptime(uptimeSeconds)}</span>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="px-6 py-2 rounded-xl text-[10px] font-bold text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors uppercase tracking-widest">
            Build sensor sim
          </button>
          <button className="px-6 py-2 rounded-xl text-[10px] font-bold text-white bg-teal hover:bg-teal-dark transition-all shadow-lg shadow-teal/20 uppercase tracking-widest">
            Agent logic
          </button>
        </div>
      </footer>
    </div>
  );
};

export default GridPulseDashboard;
