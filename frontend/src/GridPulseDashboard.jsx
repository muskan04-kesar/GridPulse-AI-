import React, { useState, useEffect, useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, Cell, AreaChart, Area
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
  { id: 'F-101', target: 'T-07', targetName: 'Civil Lines Substation', severity: 'Critical/Safety Hazard', type: 'High-Impedance (Vegetation)', status: 'action_required', time: '12:04:33', confidence: '94%', agentAssigned: 'A-A' },
  { id: 'F-104', target: 'T-12', targetName: 'Katra Crossing', severity: 'Scheduled/Maintenance', type: 'Insulator Degradation', status: 'scheduled', time: '13:15:00', confidence: '88%', agentAssigned: 'A-W' },
  { id: 'F-201', target: 'T-03', targetName: 'MG Road Primary', severity: 'Transient/Fixed', type: 'Voltage Sag (Cleared)', status: 'closed', time: '09:30:12', confidence: '99%', agentAssigned: 'Auto' },
  { id: 'F-198', target: 'T-01', targetName: 'Civil Lines West', severity: 'Transient/Fixed', type: 'Overcurrent Peak', status: 'closed', time: '08:45:00', confidence: '97%', agentAssigned: 'Auto' },
  { id: 'F-195', target: 'T-09', targetName: 'High Court Zone', severity: 'Transient/Fixed', type: 'Harmonic Distortion', status: 'closed', time: '07:20:00', confidence: '92%', agentAssigned: 'Auto' },
];

const PREDICTIVE_TREND_DATA = [
  { month: 'Jan', actual: 12, predicted: 10 },
  { month: 'Feb', actual: 15, predicted: 14 },
  { month: 'Mar', actual: 8, predicted: 9 },
  { month: 'Apr', actual: 20, predicted: 19 },
  { month: 'May', actual: 14, predicted: 15 },
  { month: 'Jun', actual: 9, predicted: 8 },
];

const HOTSPOTS_DATA = [
  { target: 'T-07', targetName: 'Civil Lines Sub', count: 14, trend: '+3', risk: 'High' },
  { target: 'T-12', targetName: 'Katra Crossing', count: 9, trend: '-1', risk: 'Medium' },
  { target: 'T-01', targetName: 'Civil Lines West', count: 5, trend: '0', risk: 'Low' },
  { target: 'T-09', targetName: 'High Court Zone', count: 3, trend: '-2', risk: 'Low' },
];

const AGENTS = [
  {
    id: 'A-W', name: 'Watcher', role: 'Monitoring Zone 4 stream', type: 'red', avatar: 'W',
    efficiency: '99.4%', avgTime: '1.2s', falsePos: '0.01%', confidence: 94,
    thoughts: [
      "Scanning input streams across T-01 to T-12...",
      "Analyzing normal 50Hz sine waves...",
      "No anomalies detected in T-01 through T-06.",
      "T-07 Voltage Unbalance detected (14% deviation).",
      "Flagging Substation T-07 for Analyst review.",
      "Confidence: 94% — Fault signature isolated."
    ]
  },
  {
    id: 'A-A', name: 'Analyst', role: 'Busy — verifying T-12', type: 'blue', avatar: 'A',
    efficiency: '96.8%', avgTime: '4.5s', falsePos: '2.1%', confidence: 88,
    thoughts: [
      "Receiving flagged data block for T-12 from Watcher.",
      "Running specialized FFT feature extraction...",
      "3rd harmonic spike detected. High crest factor.",
      "Cross-referencing with local grid topology...",
      "Weather conditions check: High winds in Zone 4.",
      "Conclusion: Vegetation contact / High-Impedance fault likely."
    ]
  },
];

const TECHNICIANS = [
  { id: 'TECH-042', name: 'Rajesh Kumar', role: 'Transformer Specialist', status: 'en route', distance: '0.8 km from T-07', efficiency: 94, info: 'ETA 11 min' },
  { id: 'TECH-019', name: 'Pradeep Verma', role: 'Line Specialist', status: 'available', distance: '1.2 km from T-12', efficiency: 98, info: 'Stationed at Zone 4 Base' },
  { id: 'TECH-088', name: 'Amit Singh', role: 'Vegetation Clearing', status: 'on-site', distance: '0.0 km from T-03', efficiency: 89, info: 'Working on F-201' },
  { id: 'TECH-112', name: 'Vikram Das', role: 'General Maintenance', status: 'off-shift', distance: '8.4 km from Base', efficiency: 92, info: 'Rest Period' },
];

const GridPulseDashboard = () => {
  const [selectedFaultId, setSelectedFaultId] = useState('F-101');
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [activeTab, setActiveTab] = useState('Overview');
  const [techFilter, setTechFilter] = useState('All');

  const selectedAgent = AGENTS.find(a => a.id === selectedAgentId);
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
            {activeTab === 'Overview' && (
              <>
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
              </>
            )}

            {activeTab === 'Agents' && (
              <div className="flex-1 overflow-y-auto space-y-6 min-h-0 pr-2 pb-4">
                {AGENTS.map(agent => (
                  <div key={agent.id} className="bg-[#0F172A] border border-slate-700/50 rounded-3xl p-6 shadow-xl flex flex-col gap-6 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-teal-500/5 -translate-y-1/2 translate-x-1/3 rounded-full blur-[80px]" />
                    {/* Header */}
                    <div className="flex justify-between items-start relative z-10">
                      <div className="flex items-center gap-4">
                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-bold text-white shadow-lg ${agent.type === 'red' ? 'bg-red shadow-red/20' : 'bg-blue shadow-blue/20'}`}>
                          {agent.avatar}
                        </div>
                        <div>
                          <h2 className="text-white font-bold text-xl leading-none mb-1 flex items-center gap-2">
                            {agent.name} <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
                          </h2>
                          <p className="text-slate-400 text-sm font-mono">{agent.role}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Live Confidence</p>
                        <p className={`text-3xl font-mono tracking-tighter leading-none ${agent.confidence > 90 ? 'text-teal-400' : 'text-blue-400'}`}>
                          {agent.confidence}%
                        </p>
                      </div>
                    </div>

                    {/* Content Split */}
                    <div className="flex flex-col xl:flex-row gap-6 relative z-10">
                      {/* Logs */}
                      <div className="flex-[2] bg-[#0a0f1c] rounded-2xl p-5 border border-slate-800/50 shadow-inner">
                        <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                          <Activity className="w-3 h-3 text-teal-400" /> Active Reasoning Chain
                        </h3>
                        <div className="space-y-4 font-mono text-xs text-slate-300">
                          {agent.thoughts.map((t, idx) => (
                            <div key={idx} className="flex items-start gap-3">
                              <span className="text-teal-400 mt-0.5">&gt;</span>
                              <p className="leading-relaxed">{t}</p>
                            </div>
                          ))}
                          <div className="flex items-center gap-2 animate-pulse mt-4 text-slate-500">
                            <span className="w-1.5 h-3 bg-slate-500 inline-block opacity-50" /> Processing stream...
                          </div>
                        </div>
                      </div>

                      {/* Metrics & Decisions */}
                      <div className="flex-1 flex flex-col gap-4">
                        <div className="bg-slate-800/30 rounded-2xl p-5 border border-slate-700/50">
                          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-4">Efficiency Metrics</h3>
                          <div className="space-y-3 text-xs">
                            <div className="flex justify-between items-center border-b border-slate-800/50 pb-2">
                              <span className="text-slate-400">Success Rate</span>
                              <span className="text-white font-mono font-bold">{agent.efficiency}</span>
                            </div>
                            <div className="flex justify-between items-center border-b border-slate-800/50 pb-2">
                              <span className="text-slate-400">Avg Diagnosis</span>
                              <span className="text-white font-mono font-bold">{agent.avgTime}</span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-slate-400">False Positives</span>
                              <span className="text-amber-400 font-mono font-bold">{agent.falsePos}</span>
                            </div>
                          </div>
                        </div>

                        <div className="bg-teal-900/20 rounded-2xl p-5 border border-teal-500/20 flex-1 flex flex-col justify-center">
                          <h3 className="text-[10px] font-bold text-teal-500 uppercase tracking-[0.2em] mb-2 flex items-center gap-2">
                            <ShieldCheck className="w-3 h-3" /> Latest Decision
                          </h3>
                          <p className="text-sm text-teal-50 leading-relaxed">
                            {agent.id === 'A-W' ? 'Flagged critical anomaly at T-07. Forwarded verified signature to Analyst.' : 'Confirmed vegetation contact at T-12. Dispatching nearest technician.'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'Fault log' && (
              <div className="flex-1 overflow-y-auto space-y-4 min-h-0 pr-2 custom-scrollbar pb-4">
                <div className="flex items-center justify-between bg-white px-6 py-5 rounded-3xl border border-gray-100 shadow-sm mb-4 sticky top-0 z-10">
                  <h2 className="text-xs font-bold text-slate-700 uppercase tracking-[0.2em] flex items-center gap-2">
                    <ShieldAlert className="w-5 h-5 text-red" /> Operational Workflow Hub
                  </h2>
                  <div className="flex gap-4">
                    <button className="text-[10px] font-bold uppercase tracking-widest bg-slate-50 text-slate-600 px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-100 transition-colors">Export Report</button>
                  </div>
                </div>

                {FAULT_LOG.map(f => (
                  <div key={f.id} className={`bg-white border rounded-3xl p-6 shadow-sm transition-all hover:shadow-md flex flex-col gap-6 ${selectedFaultId === f.id ? 'border-teal ring-2 ring-teal/20' : 'border-gray-200'}`}>
                    <div className="flex flex-col xl:flex-row xl:justify-between items-start gap-5">
                      <div className="flex items-start gap-4">
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 shadow-inner
                            ${f.severity.includes('Critical') ? 'bg-red text-white shadow-red/20' :
                            f.severity.includes('Maintenance') ? 'bg-amber-100 text-amber-600' : 'bg-teal-50 text-teal-600'}`}>
                          <Activity className="w-6 h-6" />
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2 mb-1.5">
                            <h3 className="font-bold text-slate-800 text-[15px] tracking-tight">{f.id} — {f.targetName} ({f.target})</h3>
                            <span className={`text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-md border shadow-sm
                               ${f.severity.includes('Critical') ? 'bg-red-50 text-red border-red/20' :
                                f.severity.includes('Maintenance') ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-teal-50 text-teal-700 border-teal-200'}`}>
                              {f.severity}
                            </span>
                          </div>
                          <p className="text-xs font-medium text-slate-500 flex items-center gap-3">
                            <span>Detected: <span className="text-slate-700 font-bold">{f.type}</span></span>
                            <span className="w-1 h-1 bg-slate-300 rounded-full" />
                            <span>Confidence: <span className="font-mono text-slate-700">{f.confidence}</span></span>
                            <span className="w-1 h-1 bg-slate-300 rounded-full" />
                            <span>Time: <span className="font-mono text-slate-700">{f.time}</span></span>
                          </p>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 mt-2 xl:mt-0">
                        {f.status !== 'closed' ? (
                          <>
                            <button className="flex items-center gap-2 px-4 py-2 bg-[#0F172A] text-white hover:bg-slate-800 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all shadow-md hover:shadow-lg active:scale-95">
                              Dispatch Crew
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2 bg-white text-slate-600 hover:bg-slate-50 border border-slate-200 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all shadow-sm active:scale-95">
                              Auto-Reset
                            </button>
                            <button className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all shadow-sm active:scale-95 border
                               ${f.severity.includes('Critical') ? 'bg-red-50 text-red-600 hover:bg-red-100 border-red-200' : 'bg-slate-50 text-slate-400 border-transparent cursor-not-allowed'}`}>
                              Escalate to Senior
                            </button>
                          </>
                        ) : (
                          <div className="flex items-center gap-2 px-4 py-2 bg-teal-50 border border-teal-100 rounded-xl text-[10px] font-bold uppercase tracking-wider text-teal-700 shrink-0">
                            <ShieldCheck className="w-4 h-4" /> Issue Closed
                          </div>
                        )}
                      </div>
                    </div>

                    {f.status !== 'closed' && (
                      <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs bg-slate-50/50 -mx-6 -mb-6 px-6 pb-5 rounded-b-3xl">
                        <div className="flex items-center gap-3 text-slate-500 font-mono mt-1">
                          <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                          </span>
                          Agent <span className="text-slate-700 font-bold ml-1">{f.agentAssigned}</span> actively tracking logic...
                        </div>
                        <button
                          onClick={() => { setSelectedFaultId(f.id); setActiveTab('Overview'); }}
                          className="text-teal-600 font-bold hover:text-teal-700 transition-colors group flex items-center gap-1.5 text-[10px] uppercase tracking-widest bg-white border border-teal-100 px-3 py-1.5 rounded-lg shadow-sm hover:shadow-md"
                        >
                          <MapIcon className="w-3 h-3" /> Drill-down Map <span className="group-hover:translate-x-1 transition-transform">→</span>
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'Analytics' && (
              <div className="flex-1 overflow-y-auto space-y-6 min-h-0 pr-2 pb-4 custom-scrollbar">
                {/* KPI Row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-teal-50 border border-teal-100 rounded-3xl p-6 shadow-sm relative overflow-hidden group hover:border-teal-300 transition-colors">
                    <div className="absolute -right-4 -top-4 text-teal-500/10 group-hover:scale-110 transition-transform"><IndianRupee className="w-32 h-32" /></div>
                    <h3 className="text-xs font-bold text-teal-800 uppercase tracking-[0.2em] mb-2 flex items-center gap-2 relative z-10"><TrendingUp className="w-4 h-4" /> Loss Prevented</h3>
                    <div className="flex items-end gap-2 relative z-10 mt-1">
                      <span className="text-4xl font-mono tracking-tighter text-teal-600 font-bold">₹14.2 L</span>
                    </div>
                    <p className="mt-4 text-[10px] font-bold text-teal-800 bg-teal-100/60 inline-flex px-2 py-1 rounded-md relative z-10 shadow-sm border border-teal-200/50">+₹4.5 Lakhs saved specifically avoiding T-07 blowout.</p>
                  </div>

                  <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm group hover:border-blue-300 transition-colors">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-[0.2em] mb-2 flex items-center gap-2"><Activity className="w-4 h-4 text-blue-500" /> Model Accuracy</h3>
                    <div className="flex items-end gap-2 mt-1">
                      <span className="text-4xl font-mono tracking-tighter text-blue-600 font-bold">96.4%</span>
                    </div>
                    <p className="mt-4 text-[10px] font-bold text-slate-500 bg-slate-50 inline-flex px-2 py-1 rounded-md border border-slate-100">Based on 1,420 simulated anomaly patterns.</p>
                  </div>

                  <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm group hover:border-slate-300 transition-colors">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-[0.2em] mb-2 flex items-center gap-2"><Bot className="w-4 h-4 text-slate-700" /> Auto-Diagnosis</h3>
                    <div className="flex items-end gap-2 mt-1">
                      <span className="text-4xl font-mono tracking-tighter text-slate-700 font-bold">88.5%</span>
                    </div>
                    <p className="mt-4 text-[10px] font-bold text-slate-500 bg-slate-50 inline-flex px-2 py-1 rounded-md border border-slate-100">Percentage of faults resolved without human input.</p>
                  </div>
                </div>

                {/* Main charts row */}
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 h-80">
                  <div className="xl:col-span-2 bg-white rounded-3xl border border-gray-100 shadow-sm p-6 flex flex-col">
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-6 gap-4">
                      <div>
                        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-[0.2em]">Predictive Maintenance Trend</h3>
                        <p className="text-[10px] text-slate-400 font-medium mt-1">Comparing Actual Transformer Failures vs. AI Predictive Alerts generated.</p>
                      </div>
                      <div className="flex gap-4">
                        <div className="flex items-center gap-2"><div className="w-3 h-1 bg-red-400 rounded-full" /><span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Actuals</span></div>
                        <div className="flex items-center gap-2"><div className="w-3 h-1 border-dashed border border-blue-400 bg-blue-50 rounded-full" /><span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">AI Predictions</span></div>
                      </div>
                    </div>

                    <div className="flex-1 w-full min-h-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={PREDICTIVE_TREND_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <defs>
                            <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor={COLORS.blue} stopOpacity={0.2} />
                              <stop offset="95%" stopColor={COLORS.blue} stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor={COLORS.red} stopOpacity={0.1} />
                              <stop offset="95%" stopColor={COLORS.red} stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#94A3B8', fontWeight: 600 }} dy={10} />
                          <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#94A3B8', fontWeight: 600 }} dx={-10} />
                          <Tooltip contentStyle={{ fontSize: '10px', borderRadius: '12px', border: '1px solid #E2E8F0', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }} />
                          <Area type="monotone" dataKey="actual" stroke={COLORS.red} strokeWidth={2} fillOpacity={1} fill="url(#colorActual)" />
                          <Area type="monotone" dataKey="predicted" stroke={COLORS.blue} strokeWidth={2} strokeDasharray="5 5" fillOpacity={1} fill="url(#colorPredicted)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="bg-[#0F172A] rounded-3xl border border-slate-700 p-6 flex flex-col shadow-inner">
                    <div className="mb-6">
                      <h3 className="text-xs font-bold text-slate-200 uppercase tracking-[0.2em]">Regional Hotspots</h3>
                      <p className="text-[10px] text-slate-500 font-medium mt-1">Transformers with Highest Fault Frequency.</p>
                    </div>

                    <div className="flex-1 flex flex-col gap-3 justify-center">
                      {HOTSPOTS_DATA.map((h, i) => (
                        <div key={i} className="flex justify-between items-center p-3 rounded-2xl bg-slate-800/50 border border-slate-700/50 hover:bg-slate-800 transition-colors group">
                          <div>
                            <p className="text-xs font-bold text-white group-hover:text-teal-400 transition-colors">{h.targetName}</p>
                            <p className="text-[10px] font-mono text-slate-500 mt-0.5">{h.target}</p>
                          </div>
                          <div className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <span className={`text-[10px] font-bold ${h.trend.startsWith('+') ? 'text-red-400' : 'text-teal-400'}`}>{h.trend}</span>
                              <span className="text-sm font-mono font-bold text-slate-300">{h.count} faults</span>
                            </div>
                            <div className="flex items-center justify-end gap-1.5 mt-1.5">
                              {Array.from({ length: 3 }).map((_, idx) => (
                                <div key={idx} className={`w-3.5 h-1.5 rounded-full ${idx < (h.risk === 'High' ? 3 : h.risk === 'Medium' ? 2 : 1) ? (h.risk === 'High' ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' : h.risk === 'Medium' ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]' : 'bg-teal-500 shadow-[0_0_8px_rgba(20,184,166,0.5)]') : 'bg-slate-700'}`} />
                              ))}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Technicians' && (
              <div className="flex-1 overflow-y-auto space-y-6 min-h-0 pr-2 custom-scrollbar pb-4">
                {/* Header */}
                <div className="flex items-center justify-between bg-white px-6 py-5 rounded-3xl border border-gray-100 shadow-sm sticky top-0 z-10">
                  <h2 className="text-xs font-bold text-slate-700 uppercase tracking-[0.2em] flex items-center gap-2">
                    <User className="w-5 h-5 text-[#899A7A]" /> Dispatch Command Center
                  </h2>

                  {/* Status Toggles */}
                  <div className="flex bg-slate-100 p-1.5 rounded-xl gap-1">
                    {['All', 'Available', 'En Route', 'On-Site', 'Off-Shift'].map(status => (
                      <button
                        key={status}
                        onClick={() => setTechFilter(status)}
                        className={`px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all
                           ${techFilter === status ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                      >
                        {status}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Technician Cards */}
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  {TECHNICIANS.filter(t => techFilter === 'All' || t.status.toLowerCase() === techFilter.toLowerCase()).map(t => {
                    const isAvailable = t.status === 'available';
                    const isBusy = t.status === 'en route' || t.status === 'on-site';
                    const colorClass = isAvailable ? 'text-[#899A7A] border-[#899A7A]/30 bg-[#899A7A]/10' :
                      isBusy ? 'text-[#C87C6C] border-[#C87C6C]/30 bg-[#C87C6C]/10' :
                        'text-slate-400 border-slate-200 bg-slate-50';

                    return (
                      <div key={t.id} className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6 flex flex-col gap-6 hover:shadow-md transition-shadow group">
                        <div className="flex justify-between items-start">
                          <div className="flex gap-4 items-center">
                            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center border-2 border-white shadow-sm ring-1 ring-slate-200 overflow-hidden">
                              <img src={`https://api.dicebear.com/7.x/notionists/svg?seed=${t.name}&backgroundColor=f1f5f9`} alt="avatar" className="w-full h-full object-cover" />
                            </div>
                            <div>
                              <h3 className="text-sm font-bold text-slate-800 tracking-tight flex items-center gap-2">
                                {t.name}
                                <span className="text-[9px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">{t.id}</span>
                              </h3>
                              <p className="text-xs text-slate-500 font-medium mt-0.5">{t.role}</p>
                            </div>
                          </div>

                          {/* Efficiency Score */}
                          <div className="text-right flex flex-col items-end gap-1.5">
                            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Resolution Rate</span>
                            <div className="flex items-center gap-1 bg-amber-50 text-amber-700 font-mono font-bold text-xs px-2.5 py-1 rounded-lg border border-amber-200 shadow-sm">
                              ★ {t.efficiency}%
                            </div>
                          </div>
                        </div>

                        {/* Status & Details */}
                        <div className="grid grid-cols-2 gap-3 bg-slate-50 rounded-2xl p-4 border border-slate-100">
                          <div className="flex flex-col gap-1.5">
                            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Status / Activity</span>
                            <span className={`text-[10px] font-bold uppercase tracking-widest px-2.5 py-1.5 rounded-lg border inline-flex items-center gap-2 w-fit ${colorClass}`}>
                              {isBusy && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
                              {t.status}
                            </span>
                          </div>
                          <div className="flex flex-col gap-1.5">
                            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Proximity Magic</span>
                            <span className="text-xs font-bold text-slate-700 bg-white border border-slate-200 px-2.5 py-1.5 rounded-lg flex items-center gap-2 w-fit shadow-sm"><MapIcon className="w-3 h-3 text-teal-600" /> {t.distance}</span>
                          </div>
                        </div>

                        {/* Action / Footer */}
                        <div className="flex justify-between items-center mt-auto pt-2">
                          <div className="flex items-center gap-2 text-xs font-medium text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100 shadow-inner inline-flex w-fit">
                            <Clock className="w-3.5 h-3.5 text-slate-400" /> {t.info}
                          </div>
                          <button
                            disabled={t.status === 'off-shift'}
                            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all shadow-sm
                             ${t.status === 'off-shift' ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200' : 'bg-[#0F172A] text-white hover:bg-slate-800 hover:shadow-md active:scale-95'}`}
                          >
                            <Bot className="w-3.5 h-3.5" /> Auto-Dispatch
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {activeTab !== 'Overview' && activeTab !== 'Agents' && activeTab !== 'Fault log' && activeTab !== 'Analytics' && activeTab !== 'Technicians' && (
              <div className="flex-1 flex items-center justify-center bg-white rounded-3xl border border-gray-100 shadow-sm border-dashed">
                <div className="text-center">
                  <p className="text-gray-400 font-bold uppercase tracking-widest text-xs">{activeTab} View</p>
                  <p className="text-gray-300 text-xs mt-2 font-mono">Module in development</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Sidebar */}
          <aside className="w-[248px] flex flex-col gap-6 shrink-0 h-full">
            {/* Fault Log */}
            <div className="flex-[3] bg-white rounded-3xl border border-gray-100 shadow-sm flex flex-col min-h-0">
              <div className="px-5 py-4 border-b border-gray-50 flex justify-between items-center">
                <h2 className="text-[11px] font-bold text-gray-600 uppercase tracking-widest">Active Logs</h2>
                <span className="text-[10px] font-mono font-bold text-gray-400">Total: 5</span>
              </div>
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 custom-scrollbar">
                {FAULT_LOG.map(f => (
                  <button
                    key={f.id}
                    onClick={() => { setSelectedFaultId(f.id); setActiveTab('Overview'); }}
                    className={`w-full text-left p-3 rounded-2xl transition-all border group
                      ${selectedFaultId === f.id ? 'bg-teal-light border-teal/20' : 'bg-white border-transparent hover:border-slate-300 shadow-sm'}`}
                  >
                    <div className="flex justify-between items-start mb-1.5">
                      <span className={`text-[8px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-md ${f.severity.includes('Critical') ? 'bg-red text-white' : f.severity.includes('Maintenance') ? 'bg-amber-100 text-amber-800' : 'bg-teal-100 text-teal-800'}`}>
                        {f.severity.split('/')[0]}
                      </span>
                      <span className="text-[9px] font-mono text-gray-400">{f.time.slice(0, 5)}</span>
                    </div>
                    <p className="text-xs font-bold text-gray-800">{f.target} <span className="font-medium text-[10px] text-gray-500 block truncate">{f.targetName}</span></p>
                    <div className="flex justify-between items-end mt-2">
                      <p className="text-[9px] font-bold uppercase tracking-widest text-[#1D9E75] opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"><MapIcon className="w-2.5 h-2.5" /> Fly to map</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* AI Agents & Technicians */}
            <div className="flex-[2] bg-[#0F172A] rounded-3xl p-5 shadow-inner flex flex-col gap-4">
              <h2 className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-1">AI Agents on Duty</h2>
              <div className="space-y-2">
                {AGENTS.map(a => (
                  <button
                    key={a.id}
                    onClick={() => setSelectedAgentId(a.id)}
                    className="flex gap-3 w-full text-left p-2 rounded-xl hover:bg-slate-800/50 transition-colors cursor-pointer group"
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white shadow-lg shrink-0 transition-transform group-hover:scale-105 ${a.type === 'red' ? 'bg-red' : 'bg-blue'}`}>
                      {a.avatar}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] font-bold text-white leading-none mb-1 group-hover:text-teal-400 transition-colors">{a.name}</p>
                      <p className={`text-[9px] font-bold capitalize truncate ${a.type === 'red' ? 'text-teal-400' : 'text-blue-400'}`}>
                        {a.role}
                      </p>
                    </div>
                  </button>
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

      {/* Agent Pop-out Modal */}
      {selectedAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 sm:p-12 animate-in fade-in duration-200">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setSelectedAgentId(null)} />
          <div className="relative bg-[#0F172A] border border-slate-700 w-full max-w-2xl rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">

            {/* Header */}
            <div className="px-6 py-5 border-b border-slate-800 flex justify-between items-center bg-slate-900">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl font-bold text-white shadow-[0_0_15px_rgba(0,0,0,0.5)] ${selectedAgent.type === 'red' ? 'bg-red shadow-red/20' : 'bg-blue shadow-blue/20'}`}>
                  {selectedAgent.avatar}
                </div>
                <div>
                  <h2 className="text-white font-bold text-lg leading-tight flex items-center gap-2">
                    {selectedAgent.name} Engine
                    <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
                  </h2>
                  <p className="text-slate-400 text-xs font-mono mt-0.5">{selectedAgent.role}</p>
                </div>
              </div>
              <button className="text-slate-500 hover:text-white transition-colors" onClick={() => setSelectedAgentId(null)}>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex flex-col sm:flex-row h-[26rem]">
              {/* Thought Log */}
              <div className="flex-[3] p-6 border-r border-slate-800 flex flex-col font-mono relative overflow-hidden bg-[#0a0f1c]">
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                  <Activity className="w-3 h-3 text-teal-400" /> Live Thought Log
                </h3>
                <div className="flex-1 space-y-4 overflow-y-auto pr-2 custom-scrollbar">
                  {selectedAgent.thoughts.map((thought, idx) => (
                    <div key={idx} className="text-xs text-slate-300 flex items-start gap-3">
                      <span className="text-teal-400 mt-0.5">&gt;</span>
                      <p className="leading-relaxed">{thought}</p>
                    </div>
                  ))}
                  <div className="text-xs text-slate-500 flex items-center gap-2 animate-pulse mt-4">
                    <span className="w-2 h-4 bg-slate-500 inline-block opacity-50" /> Processing stream...
                  </div>
                </div>
              </div>

              {/* Metrics Sidebar */}
              <div className="flex-[2] p-6 bg-slate-800/10 flex flex-col gap-8">
                <div>
                  <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-3">Live Confidence</h3>
                  <div className="flex items-end gap-2">
                    <span className={`text-5xl font-mono tracking-tighter ${selectedAgent.confidence > 90 ? 'text-teal-400' : 'text-blue-400'}`}>
                      {selectedAgent.confidence}
                    </span>
                    <span className="text-xl text-slate-500 font-bold mb-1">%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full mt-4 overflow-hidden relative">
                    <div className={`absolute top-0 left-0 bottom-0 ${selectedAgent.confidence > 90 ? 'bg-teal-400 shadow-[0_0_10px_rgba(29,158,117,1)]' : 'bg-blue-400 shadow-[0_0_10px_rgba(55,138,221,1)]'}`} style={{ width: `${selectedAgent.confidence}%` }} />
                  </div>
                  <p className="text-[9px] text-slate-500 mt-2 font-mono uppercase tracking-widest text-right">Target &gt; 90%</p>
                </div>

                <div>
                  <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-4">Resolution Efficiency</h3>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center border-b border-slate-800/50 pb-2">
                      <span className="text-xs text-slate-400">Success Rate</span>
                      <span className="text-sm font-bold text-white font-mono">{selectedAgent.efficiency}</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-slate-800/50 pb-2">
                      <span className="text-xs text-slate-400">Avg Diagnosis</span>
                      <span className="text-sm font-bold text-white font-mono">{selectedAgent.avgTime}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-slate-400">False Positives</span>
                      <span className="text-sm font-bold text-amber-400 font-mono">{selectedAgent.falsePos}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

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
