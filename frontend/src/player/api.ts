export interface Portfolio {
  player_id: string;
  nickname: string;
  cash: number;
  holdings: Record<string, number>;
  net_worth: number;
}

export type TradeSide = 'buy' | 'sell';

export interface PlayerApi {
  join(nickname: string): Promise<string>;
  portfolio(playerId: string, signal?: AbortSignal): Promise<Portfolio>;
  trade(playerId: string, assetId: string, side: TradeSide, qty: number): Promise<Portfolio>;
}

export class PlayerApiError extends Error {
  readonly status: number | undefined;
  readonly uncertainOutcome: boolean;

  constructor(message: string, status?: number, uncertainOutcome = false) {
    super(message);
    this.name = 'PlayerApiError';
    this.status = status;
    this.uncertainOutcome = uncertainOutcome;
  }
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('The server returned an invalid portfolio.');
  return value as Record<string, unknown>;
}

function nonemptyString(value: unknown, name: string): string {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`The server returned an invalid ${name}.`);
  return value;
}

function nonnegative(value: unknown, name: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) throw new Error(`The server returned an invalid ${name}.`);
  return value;
}

export function normalizeNickname(nickname: string): string {
  const trimmed = nickname.trim();
  if (!trimmed || Array.from(trimmed).length > 20) throw new Error('Enter a nickname between 1 and 20 characters.');
  return trimmed;
}

export function validateTrade(assetId: string, side: TradeSide, qty: number): void {
  if (!assetId.trim()) throw new Error('Select a star before trading.');
  if (side !== 'buy' && side !== 'sell') throw new Error('Choose buy or sell.');
  if (!Number.isFinite(qty) || qty <= 0) throw new Error('Enter a quantity greater than zero. Fractional shares are allowed.');
}

export function parsePortfolio(value: unknown, expectedPlayerId?: string): Portfolio {
  const data = object(value);
  const playerId = nonemptyString(data.player_id, 'player ID');
  if (expectedPlayerId && playerId !== expectedPlayerId) throw new Error('The server returned a different player’s portfolio.');
  const holdings = object(data.holdings);
  // Build a data-only dictionary, including safe handling of unusual asset IDs.
  const quantities = Object.fromEntries(Object.entries(holdings).map(([id, qty]) => {
    if (!id.trim()) throw new Error('The server returned an invalid holding.');
    return [id, nonnegative(qty, 'holding quantity')];
  }));
  return {
    player_id: playerId,
    nickname: nonemptyString(data.nickname, 'nickname'),
    cash: nonnegative(data.cash, 'cash balance'),
    holdings: quantities,
    net_worth: nonnegative(data.net_worth, 'net worth'),
  };
}

export function serverErrorDetail(value: unknown, fallback: string): string {
  if (!value || typeof value !== 'object' || !('detail' in value)) return fallback;
  const detail = (value as { detail: unknown }).detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item: unknown) => {
      if (!item || typeof item !== 'object' || !('msg' in item) || typeof item.msg !== 'string') return [];
      return [item.msg];
    });
    if (messages.length) return messages.join(' ');
  }
  return fallback;
}

export function createPlayerApi(options: {
  prefix?: string;
  fetch?: typeof fetch;
  timeoutMs?: number;
} = {}): PlayerApi {
  const fetchRequest = options.fetch ?? globalThis.fetch;
  const prefix = options.prefix ?? '';
  const timeoutMs = options.timeoutMs ?? 10_000;

  async function request(path: string, body?: unknown, signal?: AbortSignal): Promise<unknown> {
    const writing = body !== undefined;
    const controller = new AbortController();
    const cancel = () => controller.abort();
    signal?.addEventListener('abort', cancel, { once: true });
    if (signal?.aborted) cancel();
    const timer = setTimeout(cancel, timeoutMs);
    try {
      const response = await fetchRequest(`${prefix}${path}`, {
        method: writing ? 'POST' : 'GET',
        signal: controller.signal,
        cache: 'no-store',
        ...(writing ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
      });
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        throw new PlayerApiError('The server returned an unreadable response.', response.status, writing && (response.ok || response.status >= 500));
      }
      if (!response.ok) {
        throw new PlayerApiError(serverErrorDetail(payload, `The server returned ${response.status}.`), response.status, writing && response.status >= 500);
      }
      return payload;
    } catch (error) {
      if (error instanceof PlayerApiError) throw error;
      throw new PlayerApiError(
        controller.signal.aborted ? 'The request timed out or was interrupted.' : 'Unable to reach the game server.',
        undefined,
        writing,
      );
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener('abort', cancel);
    }
  }

  return {
    async join(nickname) {
      const name = normalizeNickname(nickname);
      const payload = await request('/join', { nickname: name });
      try {
        return nonemptyString(object(payload).player_id, 'player ID');
      } catch (error) {
        throw new PlayerApiError(error instanceof Error ? error.message : 'The join response is invalid.', undefined, true);
      }
    },
    async portfolio(playerId, signal) {
      return parsePortfolio(await request(`/portfolio/${encodeURIComponent(playerId)}`, undefined, signal), playerId);
    },
    async trade(playerId, assetId, side, qty) {
      validateTrade(assetId, side, qty);
      const payload = await request('/trade', { player_id: playerId, asset_id: assetId, side, qty });
      try {
        return parsePortfolio(payload, playerId);
      } catch (error) {
        throw new PlayerApiError(error instanceof Error ? error.message : 'The trade response is invalid.', undefined, true);
      }
    },
  };
}
