import { create } from "zustand";
import type { PersonaCore } from "../types";
import { personaApi } from "../api/client";

interface AppState {
    // Active persona
    activePersonaId: string | null;
    personas: PersonaCore[];
    loading: boolean;

    // Actions
    setActivePersona: (id: string | null) => void;
    fetchPersonas: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
    activePersonaId: null,
    personas: [],
    loading: false,

    setActivePersona: (id) => set({ activePersonaId: id }),

    fetchPersonas: async () => {
        set({ loading: true });
        try {
            const personas = await personaApi.list();
            set({ personas, loading: false });
            // Auto-select first if none selected
            if (!get().activePersonaId && personas.length > 0) {
                set({ activePersonaId: personas[0].id });
            }
        } catch {
            set({ loading: false });
        }
    },
}));
