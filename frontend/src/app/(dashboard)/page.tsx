"use client";

import { useEffect, useState } from "react";
import { motion, Variants } from "framer-motion";
import { Activity, Users, Send, MousePointerClick } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const CHART_DATA = [
  { date: "Mon", emails: 0, replies: 0, leads: 0 },
  { date: "Tue", emails: 0, replies: 0, leads: 0 },
  { date: "Wed", emails: 0, replies: 0, leads: 0 },
  { date: "Thu", emails: 0, replies: 0, leads: 0 },
  { date: "Fri", emails: 0, replies: 0, leads: 0 },
  { date: "Sat", emails: 0, replies: 0, leads: 0 },
  { date: "Sun", emails: 0, replies: 0, leads: 0 },
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-black/60 backdrop-blur-xl border border-white/10 p-4 rounded-xl shadow-2xl">
        <p className="text-white font-semibold mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2 mb-1">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
            <p className="text-sm text-muted-foreground capitalize">
              {entry.name}: <span className="text-white font-medium">{entry.value}</span>
            </p>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function DashboardHome() {
  const [stats, setStats] = useState([
    { label: "Active Leads", value: "—", icon: Users, change: "" },
    { label: "Emails Sent", value: "—", icon: Send, change: "" },
    { label: "Reply Rate", value: "—", icon: Activity, change: "" },
    { label: "Meetings Booked", value: "—", icon: MousePointerClick, change: "" },
  ]);

  const [chartData, setChartData] = useState(CHART_DATA);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/campaigns/`);
        if (response.ok) {
          const campaigns = await response.json();
          const activeCampaigns = campaigns.filter((c: any) => c.status === 'active');

          setStats([
            { label: "Active Campaigns", value: activeCampaigns.length.toString(), icon: Users, change: "" },
            { label: "Draft Messages", value: "—", icon: Send, change: "" },
            { label: "Active Sources", value: "—", icon: Activity, change: "" },
            { label: "Total Leads", value: "—", icon: MousePointerClick, change: "" },
          ]);
        }
      } catch (error) {
        console.log("Stats unavailable — system initializing");
      }
    };

    fetchStats();
  }, []);

  const container: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const item: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex items-center justify-between"
      >
        <div>
          <h2 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">
            Growth Automation Dashboard
          </h2>
          <p className="text-muted-foreground mt-2">Real-time metrics for your outreach campaigns.</p>
        </div>
      </motion.div>

      <motion.div 
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        {stats.map((stat, i) => (
          <motion.div 
            key={i} 
            variants={item}
            whileHover={{ y: -5, transition: { duration: 0.2 } }}
            className="bg-card/40 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-xl relative overflow-hidden group"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            
            <div className="flex items-center justify-between relative z-10">
              <span className="text-sm font-medium text-muted-foreground">{stat.label}</span>
              <div className="p-2 bg-white/5 rounded-lg border border-white/5 shadow-inner">
                <stat.icon className="w-4 h-4 text-primary" />
              </div>
            </div>
            <div className="mt-4 flex items-baseline gap-2 relative z-10">
              <span className="text-3xl font-bold text-foreground">{stat.value}</span>
              <span className="text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">{stat.change}</span>
            </div>
          </motion.div>
        ))}
      </motion.div>
      
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="w-full h-[500px] bg-card/40 backdrop-blur-md border border-white/5 rounded-2xl shadow-2xl p-6 relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent opacity-50" />
        <div className="relative z-10 mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Outreach Velocity</h3>
            <p className="text-sm text-muted-foreground">Volume metrics across all active campaigns (Last 7 Days)</p>
          </div>
        </div>
        <div className="w-full h-[380px] relative z-10">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorEmails" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorReplies" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorLeads" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="date" stroke="#ffffff40" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#ffffff40" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `${value}`} />
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1, strokeDasharray: '5 5' }} />
              <Area type="monotone" dataKey="emails" stroke="#8b5cf6" strokeWidth={3} fillOpacity={1} fill="url(#colorEmails)" activeDot={{ r: 6, fill: "#8b5cf6", stroke: "#000", strokeWidth: 2 }} />
              <Area type="monotone" dataKey="replies" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#colorReplies)" activeDot={{ r: 6, fill: "#10b981", stroke: "#000", strokeWidth: 2 }} />
              <Area type="monotone" dataKey="leads" stroke="#0ea5e9" strokeWidth={3} fillOpacity={1} fill="url(#colorLeads)" activeDot={{ r: 6, fill: "#0ea5e9", stroke: "#000", strokeWidth: 2 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </motion.div>
    </div>
  );
}
