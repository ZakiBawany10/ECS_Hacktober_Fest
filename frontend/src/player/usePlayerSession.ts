import { useEffect, useState, useSyncExternalStore } from 'react';
import type { MarketConnectionStatus } from '../market/types.ts';
import { createPlayerApi } from './api.ts';
import type { TradeSide } from './api.ts';
import { PlayerSessionController } from './session.ts';
import type { PlayerSessionState, SessionStorage } from './session.ts';

export interface PlayerSession extends PlayerSessionState {
  join(nickname: string): Promise<boolean>;
  trade(assetId: string, side: TradeSide, qty: number): Promise<boolean>;
  refresh(): void;
}

function browserStorage(): SessionStorage | undefined {
  try { return window.localStorage; }
  catch { return undefined; }
}

export function usePlayerSession(marketStatus: MarketConnectionStatus): PlayerSession {
  const [controller] = useState(() => new PlayerSessionController(
    createPlayerApi({ prefix: import.meta.env.DEV ? '/api' : '' }), browserStorage(),
  ));
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getSnapshot);

  useEffect(() => {
    let active = true;
    // Discarded StrictMode setup must not start a restore request.
    queueMicrotask(() => { if (active) controller.setLive(marketStatus === 'live'); });
    const timer = marketStatus === 'live'
      ? window.setInterval(() => { void controller.refresh(); }, 5_000)
      : undefined;
    return () => {
      active = false;
      window.clearInterval(timer);
      controller.pause();
    };
  }, [controller, marketStatus]);

  return { ...state, join: controller.join, trade: controller.trade, refresh: () => { void controller.refresh(); } };
}
