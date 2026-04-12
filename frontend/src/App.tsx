import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import PersonaPage from "./pages/PersonaPage";
import MemoriesPage from "./pages/MemoriesPage";
import GraphPage from "./pages/GraphPage";
import TestingLabPage from "./pages/TestingLabPage";
import PoliciesPage from "./pages/PoliciesPage";
import WritingStylePage from "./pages/WritingStylePage";
import EvaluationPage from "./pages/EvaluationPage";
import AdminPage from "./pages/AdminPage";
import TrainingLabPage from "./pages/TrainingLabPage";
import ProductionPage from "./pages/ProductionPage";
import QuickImportPage from "./pages/QuickImportPage";
import LoginPage from "./pages/LoginPage";
import { useAppStore } from "./store/useAppStore";

function RequireAuth({ children }: { children: React.ReactNode }) {
    const token = localStorage.getItem("mm_token");
    if (!token) return <Navigate to="/login" replace />;
    return <>{children}</>;
}

export default function App() {
    const fetchPersonas = useAppStore((s) => s.fetchPersonas);
    const token = localStorage.getItem("mm_token");

    useEffect(() => {
        if (token) fetchPersonas();
    }, [fetchPersonas, token]);

    return (
        <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
                path="/"
                element={
                    <RequireAuth>
                        <Layout />
                    </RequireAuth>
                }
            >
                <Route index element={<DashboardPage />} />
                <Route path="persona" element={<PersonaPage />} />
                <Route path="memories" element={<MemoriesPage />} />
                <Route path="writing-style" element={<WritingStylePage />} />
                <Route path="graph" element={<GraphPage />} />
                <Route path="policies" element={<PoliciesPage />} />
                <Route path="testing" element={<TestingLabPage />} />
                <Route path="training" element={<TrainingLabPage />} />
                <Route path="evaluation" element={<EvaluationPage />} />
                <Route path="production" element={<ProductionPage />} />
                <Route path="quick-import" element={<QuickImportPage />} />
                <Route path="admin" element={<AdminPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
        </Routes>
    );
}
