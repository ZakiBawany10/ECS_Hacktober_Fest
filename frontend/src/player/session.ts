import { normalizeNickname, PlayerApiError, validateTrade } from './api.ts';
import type { PlayerApi, Portfolio, TradeSide } from './api.ts';

export const PLAYER_STORAGE_KEY = 'star-market.player-id';

export interface SessionStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export function loadPlayerId(storage?: SessionStorage): string | undefined {
  try {
    const id = storage?.getItem(PLAYER_STORAGE_KEY)?.trim();
    return id || undefined;
  } catch {
    return undefined;
  }
}

export function storePlayerId(storage: SessionStorage | undefined, playerId?: string): boolean {
  try {
    if (!storage) return false;
    if (playerId) storage.setItem(PLAYER_STORAGE_KEY, playerId);
    else storage.removeItem(PLAYER_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}

export interface PlayerSessionState {
  portfolio: Portfolio | undefined;
  hasSession: boolean;
  busy: 'join' | 'trade' | null;
  syncing: boolean;
  stale: boolean;
  error: string | null;
  notice: string | null;
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : 'The game server request failed.';
}

/** Owns request ordering so delayed reads cannot replace a completed trade. */
export class PlayerSessionController {
  private readonly api: PlayerApi;
  private readonly storage: SessionStorage | undefined;
  private playerId: string | undefined;
  private live = false;
  private connectionEpoch = 0;
  private revision = 0;
  private readController: AbortController | undefined;
  private uncertainTrade = false;
  private actionError: string | null = null;
  private actionErrorNeedsRefresh = false;
  private refreshError: string | null = null;
  private readonly listeners = new Set<() => void>();
  private state: PlayerSessionState;

  constructor(api: PlayerApi, storage?: SessionStorage) {
    this.api = api;
    this.storage = storage;
    this.playerId = loadPlayerId(storage);
    this.state = {
      portfolio: undefined, hasSession: Boolean(this.playerId), busy: null,
      syncing: false, stale: true, error: null, notice: null,
    };
  }

  getSnapshot = (): PlayerSessionState => this.state;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  private publish(change: Partial<PlayerSessionState>): void {
    this.state = { ...this.state, ...change };
    for (const listener of this.listeners) listener();
  }

  private invalidateReads(): void {
    this.revision += 1;
    this.readController?.abort();
    this.readController = undefined;
  }

  private combinedError(): string | null {
    return [this.actionError, this.refreshError].filter(Boolean).join(' ') || null;
  }

  private reportActionError(error: string, change: Partial<PlayerSessionState> = {}, clearsOnRefresh = false): void {
    this.actionError = error;
    this.actionErrorNeedsRefresh = clearsOnRefresh;
    this.publish({ ...change, error: this.combinedError() });
  }

  private clearErrors(): void {
    this.actionError = null;
    this.actionErrorNeedsRefresh = false;
    this.refreshError = null;
  }

  private forgetPlayer(): void {
    this.invalidateReads();
    this.playerId = undefined;
    this.uncertainTrade = false;
    this.clearErrors();
    storePlayerId(this.storage);
    this.publish({ portfolio: undefined, hasSession: false, stale: true, syncing: false, error: null,
      notice: 'Your player is no longer on the server. The game may have restarted. Enter your name to start again.' });
  }

  setLive(live: boolean): void {
    const reconnected = live && !this.live;
    if (live !== this.live) this.connectionEpoch += 1;
    this.live = live;
    if (!live) {
      this.invalidateReads();
      this.publish({ stale: true, syncing: false });
    } else if (reconnected && this.playerId && !this.state.busy) {
      void this.refresh();
    }
  }

  pause(): void {
    this.setLive(false);
  }

  refresh = async (): Promise<boolean> => {
    const playerId = this.playerId;
    // Polling and manual refresh share an in-flight read instead of aborting a slow request.
    if (!playerId || this.state.busy || this.readController) return false;
    this.invalidateReads();
    const revision = this.revision;
    const controller = new AbortController();
    this.readController = controller;
    this.publish({ syncing: true });
    try {
      const portfolio = await this.api.portfolio(playerId, controller.signal);
      if (revision !== this.revision || playerId !== this.playerId) return false;
      const notice = this.uncertainTrade
        ? 'Portfolio refreshed. Check your holdings and cash before placing another order.'
        : this.state.notice;
      if (this.uncertainTrade || this.actionErrorNeedsRefresh) {
        this.actionError = null;
        this.actionErrorNeedsRefresh = false;
      }
      this.uncertainTrade = false;
      this.refreshError = null;
      this.publish({ portfolio, stale: !this.live, syncing: false, error: this.combinedError(), notice });
      return true;
    } catch (error) {
      if (revision !== this.revision || playerId !== this.playerId) return false;
      if (error instanceof PlayerApiError && error.status === 404) this.forgetPlayer();
      else {
        this.refreshError = `Unable to refresh your portfolio. ${message(error)}`;
        this.publish({ stale: true, syncing: false, error: this.combinedError() });
      }
      return false;
    } finally {
      if (revision === this.revision) this.readController = undefined;
    }
  };

  // Checking a saved player is read-only and does not start the shared simulation.
  resume = (): Promise<boolean> => this.refresh();

  join = async (nickname: string): Promise<boolean> => {
    if (this.state.busy || this.playerId) return false;
    let name: string;
    try { name = normalizeNickname(nickname); }
    catch (error) { this.reportActionError(message(error)); return false; }
    // Joining starts the simulation, so it must work before opening the market feed.
    this.invalidateReads();
    this.clearErrors();
    this.publish({ busy: 'join', error: null, notice: null });
    try {
      this.playerId = await this.api.join(name);
      const saved = storePlayerId(this.storage, this.playerId);
      this.publish({ hasSession: true, stale: true, notice: saved ? null : 'This browser could not save your player. Keep this page open to keep your session.' });
      return true;
    } catch (error) {
      const uncertain = error instanceof PlayerApiError && error.uncertainOutcome;
      this.reportActionError(uncertain
        ? 'Joining may have succeeded, but the response was lost. No automatic retry was sent. Check the connection before joining again.'
        : message(error));
      return false;
    } finally {
      this.publish({ busy: null });
      if (this.playerId && this.live) void this.refresh();
    }
  };

  trade = async (assetId: string, side: TradeSide, qty: number): Promise<boolean> => {
    const playerId = this.playerId;
    if (!playerId || this.state.busy) return false;
    if (!this.live || this.state.stale) {
      this.reportActionError(this.uncertainTrade
        ? 'The previous order outcome is uncertain. Refresh your portfolio and check your holdings before trading again.'
        : 'Reconnect and refresh your portfolio before placing an order.', {}, true);
      return false;
    }
    try { validateTrade(assetId, side, qty); }
    catch (error) { this.reportActionError(message(error)); return false; }
    this.invalidateReads();
    this.clearErrors();
    const connectionEpoch = this.connectionEpoch;
    this.publish({ busy: 'trade', syncing: false, error: null, notice: null });
    let verifyPlayer = false;
    try {
      const portfolio = await this.api.trade(playerId, assetId, side, qty);
      if (playerId !== this.playerId) return false;
      if (connectionEpoch !== this.connectionEpoch) {
        // A reply from before reconnect may belong to the server that just restarted.
        this.publish({ stale: true, notice: 'Order response received. Refreshing your portfolio after the connection changed.' });
      } else {
        this.publish({ portfolio, stale: !this.live, notice: `${side === 'buy' ? 'Buy' : 'Sell'} order completed.` });
      }
      return true;
    } catch (error) {
      const uncertain = error instanceof PlayerApiError && error.uncertainOutcome;
      if (uncertain) {
        this.uncertainTrade = true;
        this.reportActionError('The order outcome is uncertain. It may have executed. Refresh your portfolio and check your holdings before trading again.', { stale: true }, true);
      } else {
        verifyPlayer = error instanceof PlayerApiError && error.status === 404;
        this.reportActionError(message(error), verifyPlayer ? { stale: true } : {});
      }
      return false;
    } finally {
      this.publish({ busy: null });
      if ((verifyPlayer || connectionEpoch !== this.connectionEpoch) && this.live) void this.refresh();
    }
  };
}
