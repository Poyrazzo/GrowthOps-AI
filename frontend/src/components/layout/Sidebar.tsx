"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LayoutDashboard, Megaphone, Users, LayoutList, CheckSquare, Settings, Menu, X, Rocket, Briefcase, Activity } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const menuItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/" },
  { icon: Megaphone, label: "Campaigns", href: "/campaigns" },
  { icon: Users, label: "Lead Database", href: "/leads" },
  { icon: LayoutList, label: "Sources", href: "/sources" },
  { icon: CheckSquare, label: "Approvals", href: "/approvals" },
  { icon: Activity, label: "Activity Monitor", href: "/activity" },
  { icon: Briefcase, label: "Manual Tasks", href: "/tasks" },
  { icon: Settings, label: "Settings", href: "/settings" },
];

export function Sidebar() {
  const [isExpanded, setIsExpanded] = useState(true);
  const pathname = usePathname();

  return (
    <motion.aside
      initial={{ width: 260 }}
      animate={{ width: isExpanded ? 260 : 80 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="h-full bg-sidebar/80 backdrop-blur-xl border-r border-sidebar-border flex flex-col relative z-20"
    >
      <div className="p-4 flex items-center justify-between">
        <AnimatePresence mode="popLayout">
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="flex items-center gap-2 overflow-hidden whitespace-nowrap"
            >
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-[0_0_15px_rgba(var(--primary),0.5)]">
                <Rocket className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="font-bold text-lg bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-400">
                GrowthOps
              </span>
            </motion.div>
          )}
        </AnimatePresence>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-2 rounded-md hover:bg-white/5 transition-colors text-muted-foreground hover:text-foreground"
        >
          {isExpanded ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5 mx-auto" />}
        </button>
      </div>

      <nav className="flex-1 mt-6 px-3 flex flex-col gap-2">
        {menuItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link key={item.label} href={item.href} className="relative group block">
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute inset-0 bg-primary/20 rounded-lg border border-primary/30"
                  initial={false}
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <div
                className={cn(
                  "relative flex items-center gap-3 px-3 py-3 rounded-lg transition-colors overflow-hidden whitespace-nowrap",
                  isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                )}
              >
                <item.icon className={cn("w-5 h-5 shrink-0", isActive ? "text-primary drop-shadow-[0_0_8px_rgba(var(--primary),0.8)]" : "")} />
                <AnimatePresence mode="popLayout">
                  {isExpanded && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: "auto" }}
                      exit={{ opacity: 0, width: 0 }}
                      transition={{ duration: 0.2 }}
                      className="font-medium"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>
            </Link>
          );
        })}
      </nav>
      
      {/* Bottom user profile placeholder */}
      <div className="p-4 border-t border-sidebar-border">
         <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-purple-600 mx-auto lg:ml-0 flex items-center justify-center shrink-0 border border-white/10 shadow-lg cursor-pointer hover:scale-105 transition-transform">
            <span className="font-bold text-sm text-white">GO</span>
         </div>
      </div>
    </motion.aside>
  );
}
