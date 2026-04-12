import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../api/client";
import { useAppStore } from "../store/useAppStore";
import { Sparkles, LogIn, UserPlus, ArrowRight } from "lucide-react";

export default function LoginPage() {
    const navigate = useNavigate();
    const fetchPersonas = useAppStore((s) => s.fetchPersonas);
    const [needsSetup, setNeedsSetup] = useState<boolean | null>(null);
    const [mode, setMode] = useState<"login" | "register" | "setup">("login");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // Check if already authenticated
        const token = localStorage.getItem("mm_token");
        if (token) {
            navigate("/", { replace: true });
            return;
        }

        // Check if first run
        authApi
            .setupStatus()
            .then((s) => {
                setNeedsSetup(s.needs_setup);
                if (s.needs_setup) setMode("setup");
            })
            .catch(() => {
                // Backend unreachable or users table missing — assume first run
                setNeedsSetup(true);
                setMode("setup");
            });
    }, [navigate]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (
            (mode === "setup" || mode === "register") &&
            password !== confirmPassword
        ) {
            setError("Passwords do not match");
            return;
        }
        if (password.length < 6) {
            setError("Password must be at least 6 characters");
            return;
        }

        setLoading(true);
        try {
            const fn =
                mode === "setup"
                    ? authApi.setup
                    : mode === "register"
                      ? authApi.register
                      : authApi.login;
            const result = await fn({ email, password });
            localStorage.setItem("mm_token", result.access_token);
            localStorage.setItem(
                "mm_user",
                JSON.stringify({
                    email: result.email,
                    is_admin: result.is_admin,
                }),
            );
            await fetchPersonas();
            navigate("/", { replace: true });
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response
                    ?.data?.detail || "Authentication failed";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    if (needsSetup === null) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <div className="animate-pulse text-slate-500">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                {/* Brand */}
                <div className="text-center mb-8">
                    <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-4">
                        <Sparkles size={28} className="text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-white tracking-tight">
                        MirrorMind
                    </h1>
                    <p className="text-sm text-slate-500 mt-1">
                        AI Clone Platform
                    </p>
                </div>

                {/* Card */}
                <div className="card p-8">
                    {mode === "setup" && (
                        <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-4 mb-6">
                            <h3 className="text-sm font-semibold text-indigo-400 mb-1">
                                First Run Setup
                            </h3>
                            <p className="text-xs text-slate-400">
                                No admin account found. Create the first admin
                                account to get started.
                            </p>
                        </div>
                    )}

                    <h2 className="text-lg font-semibold text-white mb-6">
                        {mode === "setup"
                            ? "Create Admin Account"
                            : mode === "register"
                              ? "Create Account"
                              : "Sign In"}
                    </h2>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">
                                Email
                            </label>
                            <input
                                type="email"
                                className="input"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="admin@example.com"
                                required
                                autoFocus
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">
                                Password
                            </label>
                            <input
                                type="password"
                                className="input"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                minLength={6}
                            />
                        </div>

                        {(mode === "setup" || mode === "register") && (
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                                    Confirm Password
                                </label>
                                <input
                                    type="password"
                                    className="input"
                                    value={confirmPassword}
                                    onChange={(e) =>
                                        setConfirmPassword(e.target.value)
                                    }
                                    placeholder="••••••••"
                                    required
                                    minLength={6}
                                />
                            </div>
                        )}

                        {error && (
                            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-primary w-full justify-center"
                        >
                            {loading ? (
                                "Loading..."
                            ) : mode === "setup" ? (
                                <>
                                    <ArrowRight className="w-4 h-4" /> Create
                                    Admin & Continue
                                </>
                            ) : mode === "register" ? (
                                <>
                                    <UserPlus className="w-4 h-4" /> Create
                                    Account
                                </>
                            ) : (
                                <>
                                    <LogIn className="w-4 h-4" /> Sign In
                                </>
                            )}
                        </button>
                    </form>

                    {!needsSetup && (
                        <div className="mt-6 text-center">
                            {mode === "login" ? (
                                <button
                                    onClick={() => setMode("register")}
                                    className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
                                >
                                    Don't have an account? Register
                                </button>
                            ) : mode === "register" ? (
                                <button
                                    onClick={() => setMode("login")}
                                    className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
                                >
                                    Already have an account? Sign in
                                </button>
                            ) : null}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
