import TipBox from "../components/TipBox";
import { BarChart3 } from "lucide-react";

const METRICS = [
    { name: "Style Similarity", desc: "Does the clone write like you?" },
    { name: "Tone Fidelity", desc: "Matches emotional tone for context" },
    { name: "Persona Consistency", desc: "Stays in character with identity" },
    { name: "Policy Compliance", desc: "Respects all defined rules" },
    { name: "Memory Relevance", desc: "Pulls the right memories" },
    { name: "Hallucination Risk", desc: "Invents facts? (lower = better)" },
    { name: "Artificiality", desc: "Sounds robotic? (lower = better)" },
    { name: "Emotional Appropriateness", desc: "Right emotional response" },
    { name: "Boundary Respect", desc: "Honors never-say and avoid-topics" },
    { name: "Response Usefulness", desc: "Is the reply helpful?" },
];

export default function EvaluationPage() {
    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
            <h2 className="page-header">Evaluation & Scoring</h2>

            <TipBox title="Evaluation — how good is your clone?">
                <p className="mb-2">
                    This dashboard shows{" "}
                    <strong>aggregate quality scores</strong> across all test
                    results. Each metric measures a different aspect of clone
                    fidelity.
                </p>
                <p className="mt-2">
                    <strong>Scores appear after</strong> you run tests in the
                    Testing Lab and submit evaluations. Focus on improving your
                    weakest metrics first.
                </p>
            </TipBox>

            <div className="card p-6">
                <h3 className="font-semibold text-white mb-5 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-indigo-400" /> Evaluation
                    Metrics
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                    {METRICS.map((metric) => (
                        <div
                            key={metric.name}
                            className="bg-slate-800/60 rounded-xl p-4 text-center group hover:bg-slate-800/80 transition-colors"
                        >
                            <div className="text-xs text-slate-500 mb-1 font-medium">
                                {metric.name}
                            </div>
                            <div className="text-2xl font-mono text-slate-600 my-1">
                                —
                            </div>
                            <div className="text-[10px] text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity">
                                {metric.desc}
                            </div>
                        </div>
                    ))}
                </div>
                <p className="text-sm text-slate-500 mt-5">
                    Run test scenarios in the Testing Lab, then evaluate results
                    here. Aggregate scores will appear once evaluations are
                    submitted.
                </p>
            </div>
        </div>
    );
}
