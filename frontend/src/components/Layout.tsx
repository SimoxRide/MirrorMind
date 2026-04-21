import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import {
    LayoutDashboard,
    User,
    Brain,
    PenTool,
    Network,
    Shield,
    FlaskConical,
    GraduationCap,
    BarChart3,
    Settings,
    Sparkles,
    FileText,
    Rocket,
    Puzzle,
    LogOut,
    Menu,
    X,
} from "lucide-react";
import { useAppStore } from "../store/useAppStore";

const NAV_ITEMS = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard },
    { to: "/persona", label: "Persona Core", icon: User },
    { to: "/memories", label: "Memories", icon: Brain },
    { to: "/writing-style", label: "Writing Style", icon: PenTool },
    { to: "/graph", label: "Knowledge Graph", icon: Network },
    { to: "/policies", label: "Rules & Policies", icon: Shield },
    { to: "/testing", label: "Testing Lab", icon: FlaskConical },
    { to: "/training", label: "Training Lab", icon: GraduationCap },
    { to: "/evaluation", label: "Evaluation", icon: BarChart3 },
    { to: "/production", label: "Production", icon: Rocket },
    { to: "/extensions", label: "Extensions", icon: Puzzle },
    { to: "/document-import", label: "Document Import", icon: FileText },
    { to: "/quick-import", label: "Quick Import", icon: Sparkles },
    { to: "/admin", label: "System", icon: Settings },
];

export default function Layout() {
    const location = useLocation();
    const navigate = useNavigate();
    const personas = useAppStore((s) => s.personas);
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const setActivePersona = useAppStore((s) => s.setActivePersona);
    const [sidebarOpen, setSidebarOpen] = useState(false);

    // Close sidebar on route change (mobile)
    useEffect(() => {
        setSidebarOpen(false);
    }, [location.pathname]);

    const handleLogout = () => {
        localStorage.removeItem("mm_token");
        localStorage.removeItem("mm_user");
        navigate("/login");
    };

    const sidebarContent = (
        <>
            {/* Brand */}
            <div className="px-5 py-5">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <img
                            src="/mirrormind-icon.png"
                            alt="MirrorMind"
                            className="h-10 w-10 shrink-0 object-contain"
                        />
                        <div>
                            <h1 className="text-sm font-bold text-white tracking-tight">
                                MirrorMind
                            </h1>
                            <span className="text-[10px] text-slate-500 font-medium">
                                AI Clone Platform
                            </span>
                        </div>
                    </div>
                    <button
                        onClick={() => setSidebarOpen(false)}
                        className="lg:hidden p-1 text-slate-500 hover:text-white transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Persona selector */}
                <select
                    className="mt-4 w-full bg-slate-800/80 text-sm rounded-lg px-3 py-2 border border-slate-700
                               text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40
                               focus:border-indigo-500 transition-all cursor-pointer"
                    value={activePersonaId ?? ""}
                    onChange={(e) => setActivePersona(e.target.value || null)}
                >
                    <option value="">Select persona…</option>
                    {personas.map((p) => (
                        <option key={p.id} value={p.id}>
                            {p.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-3 py-1 overflow-y-auto space-y-0.5">
                {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
                    const active =
                        to === "/"
                            ? location.pathname === "/"
                            : location.pathname.startsWith(to);
                    return (
                        <Link
                            key={to}
                            to={to}
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 ${
                                active
                                    ? "bg-indigo-600/15 text-indigo-400"
                                    : "text-slate-500 hover:bg-slate-800/60 hover:text-slate-300"
                            }`}
                        >
                            <Icon
                                size={16}
                                className={
                                    active
                                        ? "text-indigo-400"
                                        : "text-slate-600"
                                }
                            />
                            {label}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-slate-800">
                <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 px-3 py-2 w-full rounded-lg text-[13px] font-medium
                               text-slate-500 hover:bg-slate-800/60 hover:text-slate-300 transition-all duration-150"
                >
                    <LogOut size={16} className="text-slate-600" />
                    Logout
                </button>
                <div className="text-[11px] text-slate-600 mt-1 px-3">
                    v0.1.7
                </div>
            </div>
        </>
    );

    return (
        <div className="flex h-screen bg-slate-950">
            {/* Mobile top bar */}
            <div className="fixed top-0 left-0 right-0 z-40 lg:hidden bg-slate-900 border-b border-slate-800 px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                    <img
                        src="/mirrormind-icon.png"
                        alt="MirrorMind"
                        className="h-8 w-8 shrink-0 object-contain"
                    />
                    <span className="text-sm font-bold text-white">
                        MirrorMind
                    </span>
                </div>
                <button
                    onClick={() => setSidebarOpen(true)}
                    className="p-1.5 text-slate-400 hover:text-white transition-colors"
                >
                    <Menu size={22} />
                </button>
            </div>

            {/* Mobile overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar — desktop: static, mobile: slide-in drawer */}
            <aside
                className={`
                    fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 flex flex-col
                    transform transition-transform duration-300 ease-in-out
                    lg:static lg:translate-x-0 lg:w-60
                    ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
                `}
            >
                {sidebarContent}
            </aside>

            {/* Main content */}
            <main className="flex-1 overflow-y-auto bg-slate-950 pt-14 lg:pt-0">
                <Outlet />
            </main>
        </div>
    );
}
