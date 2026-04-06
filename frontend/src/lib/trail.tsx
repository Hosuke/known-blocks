import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from 'react';
import { api, type Trail, type TrailStep } from './api';

interface TrailContextType {
  recording: boolean;
  currentTrail: Trail | null;
  startTrailAndRecord: (name: string, steps: Omit<TrailStep, 'ts'>[]) => Promise<void>;
  startTrail: (name?: string) => void;
  stopTrail: () => void;
  recordStep: (step: Omit<TrailStep, 'ts'>) => void;
}

const TrailContext = createContext<TrailContextType>({
  recording: false,
  currentTrail: null,
  startTrailAndRecord: async () => {},
  startTrail: () => {},
  stopTrail: () => {},
  recordStep: () => {},
});

export function TrailProvider({ children }: { children: ReactNode }) {
  const [recording, setRecording] = useState(false);
  const [currentTrail, setCurrentTrail] = useState<Trail | null>(null);
  const trailRef = useRef<Trail | null>(null);

  const startTrail = useCallback((name?: string) => {
    api.saveTrailStep(null, { type: 'article', ts: '' }, name || '').then(res => {
      trailRef.current = res.trail;
      setCurrentTrail(res.trail);
      setRecording(true);
    }).catch(() => {});
  }, []);

  /** Start a trail and record multiple steps atomically (for deep research). */
  const startTrailAndRecord = useCallback(async (name: string, steps: Omit<TrailStep, 'ts'>[]) => {
    try {
      // Create trail with first step (no empty placeholder)
      const firstStep = steps.length > 0 ? { ...steps[0], ts: '' } : { type: 'query' as const, ts: '' };
      const res = await api.saveTrailStep(null, firstStep, name);
      let trail = res.trail;
      steps = steps.slice(1); // First step already recorded
      trailRef.current = trail;
      setCurrentTrail(trail);
      setRecording(true);

      // Record steps sequentially (await each to preserve order)
      for (const step of steps) {
        const stepRes = await api.saveTrailStep(trail.id, { ...step, ts: '' });
        trail = stepRes.trail;
      }
      trailRef.current = trail;
      setCurrentTrail(trail);
    } catch { /* */ }
  }, []);

  const stopTrail = useCallback(() => {
    setRecording(false);
    setCurrentTrail(null);
    trailRef.current = null;
  }, []);

  const recordStep = useCallback((step: Omit<TrailStep, 'ts'>) => {
    // Check both ref AND state to prevent writing after stop
    if (!trailRef.current || !recording) return;
    const trailId = trailRef.current.id;
    api.saveTrailStep(trailId, { ...step, ts: '' }).then(res => {
      // Only update if still recording the same trail
      if (trailRef.current && trailRef.current.id === trailId) {
        trailRef.current = res.trail;
        setCurrentTrail(res.trail);
      }
    }).catch(() => {});
  }, [recording]);

  return (
    <TrailContext.Provider value={{ recording, currentTrail, startTrailAndRecord, startTrail, stopTrail, recordStep }}>
      {children}
    </TrailContext.Provider>
  );
}

export const useTrail = () => useContext(TrailContext);
