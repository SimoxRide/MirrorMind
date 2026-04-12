import { useState } from "react";
import {
    ChevronDown,
    ChevronUp,
    Info,
    AlertTriangle,
    CheckCircle2,
} from "lucide-react";

interface TipBoxProps {
    title?: string;
    children: React.ReactNode;
    variant?: "info" | "warning" | "success";
    defaultOpen?: boolean;
}

const VARIANTS = {
    info: {
        border: "border-indigo-500/20",
        bg: "bg-indigo-500/5",
        icon: Info,
        iconColor: "text-indigo-400",
        titleColor: "text-indigo-300",
        textColor: "text-slate-400",
    },
    warning: {
        border: "border-amber-500/20",
        bg: "bg-amber-500/5",
        icon: AlertTriangle,
        iconColor: "text-amber-400",
        titleColor: "text-amber-300",
        textColor: "text-slate-400",
    },
    success: {
        border: "border-emerald-500/20",
        bg: "bg-emerald-500/5",
        icon: CheckCircle2,
        iconColor: "text-emerald-400",
        titleColor: "text-emerald-300",
        textColor: "text-slate-400",
    },
};

export default function TipBox({
    title = "Tip",
    children,
    variant = "info",
    defaultOpen = true,
}: TipBoxProps) {
    const [open, setOpen] = useState(defaultOpen);
    const v = VARIANTS[variant];
    const IconComp = v.icon;

    return (
        <div className={`rounded-xl border ${v.border} ${v.bg} mb-5`}>
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-4 py-3 text-left"
            >
                <div className="flex items-center gap-2">
                    <IconComp size={15} className={v.iconColor} />
                    <span className={`text-sm font-medium ${v.titleColor}`}>
                        {title}
                    </span>
                </div>
                {open ? (
                    <ChevronUp size={14} className="text-slate-600" />
                ) : (
                    <ChevronDown size={14} className="text-slate-600" />
                )}
            </button>
            {open && (
                <div
                    className={`px-4 pb-3 text-sm ${v.textColor} leading-relaxed`}
                >
                    {children}
                </div>
            )}
        </div>
    );
}
