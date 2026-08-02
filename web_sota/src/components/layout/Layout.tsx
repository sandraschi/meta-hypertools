import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface LayoutProps {
  children: ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
  onShowLogger: () => void;
  onShowHelp: () => void;
}

export function Layout({
  children,
  currentPage,
  onNavigate,
  onShowLogger,
  onShowHelp,
}: LayoutProps) {
  return (
    <div className="flex h-screen bg-[#020202] text-white overflow-hidden font-sans selection:bg-blue-500/30">
      <Sidebar currentPage={currentPage} onNavigate={onNavigate} />

      <div className="flex-1 flex flex-col min-w-0 transition-all duration-500 relative">
        {/* Background Glows */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-purple-600/5 blur-[120px] rounded-full pointer-events-none -mr-48 -mt-48" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-blue-500/5 blur-[100px] rounded-full pointer-events-none -ml-32 -mb-32" />

        <Topbar title={currentPage} onShowLogger={onShowLogger} onShowHelp={onShowHelp} />

        <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 scroll-smooth relative z-10 custom-scrollbar">
          <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-6 duration-1000">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
