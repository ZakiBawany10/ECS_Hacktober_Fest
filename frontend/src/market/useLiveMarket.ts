import { useCallback, useEffect, useRef, useState } from 'react';
import {
  applyMarketMessage,
  createMarketState,
  mergeAssetHistory,
  parseHistory,
  parseSnapshot,
  parseMarketMessage,
} from './backend.ts';
import type { BackendMarketMessage, LiveMarketState } from './backend.ts';
import type { MarketConnectionStatus, MarketView } from './types.ts';

const API_PREFIX = import.meta.env.DEV ? '/api' : '';
const REQUEST_TIMEOUT = 10_000;
// The backend normally ticks once per second. Recover from an open but stalled socket.
const FEED_IDLE_TIMEOUT = 30_000;

async function requestJson(path: string, signal: AbortSignal): Promise<unknown> {
  const request = new AbortController();
  const cancel = () => request.abort();
  signal.addEventListener('abort', cancel, { once: true });
  if (signal.aborted) cancel();
  const timeout = window.setTimeout(cancel, REQUEST_TIMEOUT);
  try {
    const response = await fetch(`${API_PREFIX}${path}`, { signal: request.signal, cache: 'no-store' });
    if (!response.ok) throw new Error(`The market server returned ${response.status}.`);
    return await response.json();
  } finally {
    window.clearTimeout(timeout);
    signal.removeEventListener('abort', cancel);
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The market connection failed.';
}

export function useLiveMarket(enabled = true): {
  market: MarketView | undefined;
  status: MarketConnectionStatus;
  error: string | null;
  retry: () => void;
} {
  const [market, setMarket] = useState<MarketView>();
  const [status, setStatus] = useState<MarketConnectionStatus>(enabled ? 'connecting' : 'offline');
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const hasLoaded = useRef(false);
  const retry = useCallback(() => setRetryKey((key) => key + 1), []);

  useEffect(() => {
    if (!enabled) {
      setMarket(undefined);
      setStatus('offline');
      setError(null);
      hasLoaded.current = false;
      return;
    }
    let active = true;
    let failures = 0;
    let retryTimer: number | undefined;
    let disposeAttempt: (() => void) | undefined;

    function connect() {
      if (!active) return;
      setStatus(hasLoaded.current ? 'reconnecting' : 'connecting');

      const controller = new AbortController();
      let socket: WebSocket | undefined;
      let closed = false;
      let state: LiveMarketState | undefined;
      let pending: BackendMarketMessage[] = [];
      let pendingNewsError: string | undefined;
      let openTimeout: number | undefined;
      let idleTimeout: number | undefined;

      const dispose = () => {
        closed = true;
        controller.abort();
        window.clearTimeout(openTimeout);
        window.clearTimeout(idleTimeout);
        if (socket) {
          socket.onopen = null;
          socket.onmessage = null;
          socket.onerror = null;
          socket.onclose = null;
          socket.close();
        }
      };
      disposeAttempt = dispose;

      const fail = (message: string) => {
        if (!active || closed) return;
        dispose();
        failures += 1;
        setError(message);
        setStatus(hasLoaded.current ? 'reconnecting' : 'offline');
        const delay = Math.min(1_000 * 2 ** Math.min(failures - 1, 4), 15_000);
        retryTimer = window.setTimeout(connect, delay);
      };

      const publish = (next: LiveMarketState) => {
        state = next;
        setMarket(next.market);
      };

      const watchForUpdates = () => {
        window.clearTimeout(idleTimeout);
        idleTimeout = window.setTimeout(
          () => fail('No live market updates received for 30 seconds. Reconnecting…'),
          FEED_IDLE_TIMEOUT,
        );
      };

      const loadSnapshot = async () => {
        try {
          const snapshot = parseSnapshot(await requestJson('/state', controller.signal));
          if (!active || closed) return;
          let next = createMarketState(snapshot);
          // Preserve both ticks and news received while the HTTP snapshot was loading.
          for (const message of pending) next = applyMarketMessage(next, message);
          if (pendingNewsError) next = { ...next, market: { ...next.market, newsError: pendingNewsError } };
          pending = [];
          pendingNewsError = undefined;
          publish(next);
          watchForUpdates();
          hasLoaded.current = true;
          failures = 0;
          setStatus('live');
          setError(null);

          await Promise.all(snapshot.assets.map(async (asset) => {
            try {
              const history = parseHistory(await requestJson(`/assets/${encodeURIComponent(asset.id)}/history`, controller.signal));
              if (!active || closed || !state) return;
              // Use the latest state, since the socket may have advanced while fetching.
              publish(mergeAssetHistory(state, asset.id, history));
            } catch (historyError) {
              if (!active || closed) return;
              // A restarted history needs a new snapshot, not an old/new session mixture.
              if (historyError instanceof Error && historyError.message.includes('server restarted')) {
                fail(historyError.message);
              } else {
                setError('Price history is unavailable. Live prices are still connected.');
              }
            }
          }));
        } catch (snapshotError) {
          fail(`Unable to load the market. ${errorMessage(snapshotError)}`);
        }
      };

      try {
        const url = new URL('/ws', window.location.href);
        url.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(url);
        openTimeout = window.setTimeout(() => fail('The market server did not respond. Retrying…'), REQUEST_TIMEOUT);
        socket.onopen = () => {
          window.clearTimeout(openTimeout);
          watchForUpdates();
          void loadSnapshot();
        };
        socket.onmessage = (event: MessageEvent<unknown>) => {
          if (!active || closed) return;
          try {
            if (typeof event.data !== 'string') throw new Error('The market server sent an invalid message.');
            const data: unknown = JSON.parse(event.data);
            const newsMessage = data !== null && typeof data === 'object' && 'type' in data && data.type === 'news';
            let message: BackendMarketMessage | null;
            try {
              message = parseMarketMessage(data);
            } catch (newsError) {
              if (!newsMessage) throw newsError;
              // A bad headline must not disconnect otherwise healthy prices and trading.
              const diagnostic = 'A news update could not be read. Reload news to catch up.';
              if (state) publish({ ...state, market: { ...state.market, newsError: diagnostic } });
              else pendingNewsError = diagnostic;
              return;
            }
            if (!message) return;
            if (state) {
              const next = applyMarketMessage(state, message);
              if (next !== state) {
                publish(next);
                if (message.type === 'tick') watchForUpdates();
              }
            } else {
              pending.push(message);
              if (message.type === 'tick') watchForUpdates();
              if (pending.length > 600) throw new Error('Market synchronisation took too long.');
            }
          } catch (messageError) {
            fail(errorMessage(messageError));
          }
        };
        socket.onerror = () => fail('Cannot connect to the market server. Retrying…');
        socket.onclose = () => fail('Market connection lost. Reconnecting…');
      } catch (connectionError) {
        fail(errorMessage(connectionError));
      }
    }

    setError(null);
    // React StrictMode runs the first setup/cleanup synchronously in development.
    // Defer opening the socket so that discarded setup never opens a connection.
    queueMicrotask(connect);
    return () => {
      active = false;
      window.clearTimeout(retryTimer);
      disposeAttempt?.();
    };
  }, [enabled, retryKey]);

  return { market, status, error, retry };
}
