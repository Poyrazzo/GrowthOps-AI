"use client";

import { Bell, Search } from "lucide-react";
import { usePathname } from "next/navigation";

export function Header() {
  const pathname = usePathname();
  
  // Quick breadcrumb logic
  const title = pathname === "/" ? "Dashboard" : pathname.replace("/", "").charAt(0).toUpperCase() + pathname.slice(2);

  return (
    <header className="h-16 flex-shrink-0 w-full bg-background/40 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold tracking-tight text-foreground drop-shadow-sm">
          {title}
        </h1>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="relative hidden md:block">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search leads, campaigns..." 
            className="w-64 bg-black/20 border border-white/10 rounded-full py-1.5 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all placeholder:text-muted-foreground"
          />
        </div>
        
        <button className="relative p-2 rounded-full hover:bg-white/5 transition-colors">
          <Bell className="w-5 h-5 text-muted-foreground" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-primary animate-pulse" />
        </button>
      </div>
    </header>
  );
}
