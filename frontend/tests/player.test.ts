import assert from 'node:assert/strict';
import test from 'node:test';
import {
  createPlayerApi, normalizeNickname, parsePortfolio, PlayerApiError, serverErrorDetail,
} from '../src/player/api.ts';
import type { PlayerApi, Portfolio } from '../src/player/api.ts';
import {
  loadPlayerId, PLAYER_STORAGE_KEY, PlayerSessionController, storePlayerId,
} from '../src/player/session.ts';
import type { SessionStorage } from '../src/player/session.ts';

function portfolio(cash = 1000, qty = 0): Portfolio {
  return { player_id: 'player-1', nickname: 'Pilot', cash, holdings: { 'star-1': qty }, net_worth: 1000 };
}

function storage(initial?: string): SessionStorage {
  const values = new Map(initial ? [[PLAYER_STORAGE_KEY, initial]] : []);
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => { values.set(key, value); },
    removeItem: (key) => { values.delete(key); },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

function api(overrides: Partial<PlayerApi> = {}): PlayerApi {
  return {
    join: async () => 'player-1',
    portfolio: async () => portfolio(),
    trade: async () => portfolio(900, 1),
    ...overrides,
  };
}

async function restored(overrides: Partial<PlayerApi> = {}) {
  const saved = storage('player-1');
  const controller = new PlayerSessionController(api(overrides), saved);
  controller.setLive(true);
  await Promise.resolve();
  return { controller, saved };
}

test('starting a named player works before the feed opens and waits for a live portfolio before trading', async () => {
  const joined = deferred<string>();
  let joins = 0;
  let reads = 0;
  const saved = storage();
  const controller = new PlayerSessionController(api({
    join: async (nickname) => { joins += 1; assert.equal(nickname, 'Pilot'); return joined.promise; },
    portfolio: async () => { reads += 1; return portfolio(); },
  }), saved);
  assert.equal(joins, 0);
  assert.equal(reads, 0);
  assert.equal(await controller.join(' '), false);
  assert.equal(joins, 0);

  const starting = controller.join(' Pilot ');
  assert.equal(await controller.join('Pilot'), false);
  assert.equal(joins, 1);
  joined.resolve('player-1');
  assert.equal(await starting, true);
  assert.equal(controller.getSnapshot().hasSession, true);
  assert.equal(controller.getSnapshot().stale, true);
  assert.equal(controller.getSnapshot().portfolio, undefined);
  assert.equal(reads, 0);
  assert.equal(loadPlayerId(saved), 'player-1');
  assert.equal(await controller.trade('star-1', 'buy', 1), false);

  controller.setLive(true);
  await Promise.resolve();
  assert.equal(reads, 1);
  assert.equal(controller.getSnapshot().stale, false);
  assert.equal(controller.getSnapshot().portfolio?.nickname, 'Pilot');
});

test('a saved player waits for an explicit resume and duplicate resumes share no extra requests', async () => {
  const result = deferred<Portfolio>();
  let reads = 0;
  let joins = 0;
  const controller = new PlayerSessionController(api({
    join: async () => { joins += 1; return 'other-player'; },
    portfolio: async () => { reads += 1; return result.promise; },
  }), storage('player-1'));
  assert.equal(reads, 0);
  assert.equal(joins, 0);
  const resuming = controller.resume();
  assert.equal(controller.getSnapshot().syncing, true);
  assert.equal(await controller.resume(), false);
  assert.equal(reads, 1);
  result.resolve(portfolio(750, 2));
  assert.equal(await resuming, true);
  assert.equal(controller.getSnapshot().portfolio?.holdings['star-1'], 2);
  assert.equal(controller.getSnapshot().stale, true);
  assert.equal(controller.getSnapshot().syncing, false);
  assert.equal(joins, 0);
});

test('an expired saved player returns to name entry without starting another player automatically', async () => {
  let joins = 0;
  const saved = storage('player-1');
  const controller = new PlayerSessionController(api({
    join: async () => { joins += 1; return 'player-2'; },
    portfolio: async () => { throw new PlayerApiError('Player not found', 404); },
  }), saved);
  assert.equal(await controller.resume(), false);
  assert.equal(controller.getSnapshot().hasSession, false);
  assert.equal(loadPlayerId(saved), undefined);
  assert.equal(joins, 0);
});

test('a failed resume keeps its saved player and can be retried explicitly', async () => {
  let reads = 0;
  const saved = storage('player-1');
  const controller = new PlayerSessionController(api({ portfolio: async () => {
    reads += 1;
    if (reads === 1) throw new PlayerApiError('Server unavailable');
    return portfolio(750, 2);
  } }), saved);
  assert.equal(await controller.resume(), false);
  assert.equal(reads, 1);
  assert.equal(controller.getSnapshot().hasSession, true);
  assert.equal(loadPlayerId(saved), 'player-1');
  assert.match(controller.getSnapshot().error ?? '', /unavailable/);
  assert.equal(await controller.resume(), true);
  assert.equal(reads, 2);
  assert.equal(controller.getSnapshot().error, null);
  assert.equal(controller.getSnapshot().stale, true);
});

test('portfolio validation accepts fractional and zero holdings, and rejects corrupt balances or identities', () => {
  const raw = portfolio(12.5, 0.125);
  assert.deepEqual(parsePortfolio(raw, 'player-1'), raw);
  for (const bad of [NaN, Infinity, -1, '100']) {
    assert.throws(() => parsePortfolio({ ...raw, cash: bad }), /cash balance/);
    assert.throws(() => parsePortfolio({ ...raw, holdings: { a: bad } }), /holding quantity/);
    assert.throws(() => parsePortfolio({ ...raw, net_worth: bad }), /net worth/);
  }
  assert.throws(() => parsePortfolio(raw, 'someone-else'), /different player/);
  assert.throws(() => parsePortfolio({ ...raw, holdings: [] }), /invalid portfolio/);
  assert.throws(() => parsePortfolio({ ...raw, nickname: '' }), /nickname/);
});

test('nicknames use the server length rules and trim whitespace', () => {
  assert.equal(normalizeNickname('  Captain  '), 'Captain');
  assert.equal(normalizeNickname('🌟'.repeat(20)), '🌟'.repeat(20));
  assert.throws(() => normalizeNickname('   '), /1 and 20/);
  assert.throws(() => normalizeNickname('a'.repeat(21)), /1 and 20/);
});

test('API sends agreed endpoints, escaped IDs and positive fractional quantities without calculating prices', async () => {
  const requests: Array<{ url: string; init: RequestInit | undefined }> = [];
  const client = createPlayerApi({ prefix: '/api', fetch: async (url, init) => {
    requests.push({ url: String(url), init });
    return Response.json(String(url).endsWith('/join') ? { player_id: 'player-1' } : portfolio(975, 0.25));
  } });
  assert.equal(await client.join(' Pilot '), 'player-1');
  await client.portfolio('player-1');
  await client.trade('player-1', 'star-1', 'buy', 0.25);
  assert.deepEqual(requests.map((entry) => entry.url), ['/api/join', '/api/portfolio/player-1', '/api/trade']);
  assert.equal(requests[0].init?.body, JSON.stringify({ nickname: 'Pilot' }));
  assert.equal(requests[2].init?.body, JSON.stringify({ player_id: 'player-1', asset_id: 'star-1', side: 'buy', qty: 0.25 }));
  assert.equal(requests[1].init?.method, 'GET');
  const escaped = createPlayerApi({ fetch: async (url) => {
    assert.equal(url, '/portfolio/a%2Fb');
    return Response.json({ ...portfolio(), player_id: 'a/b' });
  } });
  await escaped.portfolio('a/b');
});

test('invalid input never sends a request, while FastAPI rejection details reach the UI', async () => {
  let calls = 0;
  const client = createPlayerApi({ fetch: async () => {
    calls += 1;
    return Response.json({ detail: 'Not enough cash' }, { status: 400 });
  } });
  await assert.rejects(client.join(' '), /nickname/);
  for (const qty of [0, -1, Infinity, NaN]) await assert.rejects(client.trade('player-1', 'star-1', 'buy', qty), /quantity/);
  assert.equal(calls, 0);
  await assert.rejects(client.trade('player-1', 'star-1', 'buy', 0.5), (error: unknown) => {
    assert.ok(error instanceof PlayerApiError);
    assert.equal(error.message, 'Not enough cash');
    assert.equal(error.uncertainOutcome, false);
    assert.equal(error.status, 400);
    return true;
  });
  assert.equal(calls, 1);
  assert.equal(serverErrorDetail({ detail: [{ msg: 'Quantity must be positive' }] }, 'fallback'), 'Quantity must be positive');
});

test('lost, timed-out, malformed or failed write responses are uncertain and never automatically retried', async () => {
  for (const response of [
    async () => { throw new Error('network lost'); },
    async () => Response.json({ detail: 'Unexpected failure' }, { status: 500 }),
    async () => Response.json({ cash: 900 }),
    async () => new Response('not json', { status: 200 }),
  ]) {
    let calls = 0;
    const client = createPlayerApi({ fetch: async () => { calls += 1; return response(); } });
    await assert.rejects(client.trade('player-1', 'star-1', 'buy', 1), (error: unknown) => {
      assert.ok(error instanceof PlayerApiError);
      assert.equal(error.uncertainOutcome, true);
      return true;
    });
    assert.equal(calls, 1);
  }
  let calls = 0;
  const timeout = createPlayerApi({ timeoutMs: 1, fetch: async (_url, init) => {
    calls += 1;
    return new Promise<Response>((_resolve, reject) => init?.signal?.addEventListener('abort', () => reject(new Error('aborted')), { once: true }));
  } });
  await assert.rejects(timeout.join('Pilot'), (error: unknown) => error instanceof PlayerApiError && error.uncertainOutcome);
  assert.equal(calls, 1);
});

test('blocked browser storage is safe and missing storage never invents a player', () => {
  const blocked: SessionStorage = {
    getItem: () => { throw new Error('blocked'); },
    setItem: () => { throw new Error('blocked'); },
    removeItem: () => { throw new Error('blocked'); },
  };
  assert.equal(loadPlayerId(blocked), undefined);
  assert.equal(storePlayerId(blocked, 'player-1'), false);
  assert.equal(storePlayerId(blocked), false);
  assert.equal(loadPlayerId(), undefined);
  assert.equal(new PlayerSessionController(api(), blocked).getSnapshot().hasSession, false);
});

test('restored sessions remain stale until the authoritative portfolio arrives', async () => {
  const response = deferred<Portfolio>();
  const controller = new PlayerSessionController(api({ portfolio: () => response.promise }), storage('player-1'));
  assert.equal(controller.getSnapshot().hasSession, true);
  assert.equal(controller.getSnapshot().stale, true);
  controller.setLive(true);
  assert.equal(controller.getSnapshot().syncing, true);
  assert.equal(await controller.trade('star-1', 'buy', 1), false);
  response.resolve(portfolio());
  await response.promise;
  assert.equal(controller.getSnapshot().stale, false);
  assert.equal(controller.getSnapshot().portfolio?.cash, 1000);
});

test('duplicate joins are blocked and joining never happens automatically on connect', async () => {
  const response = deferred<string>();
  let joins = 0;
  const saved = storage();
  const controller = new PlayerSessionController(api({ join: () => { joins += 1; return response.promise; } }), saved);
  controller.setLive(true);
  assert.equal(joins, 0);
  const first = controller.join('Pilot');
  assert.equal(await controller.join('Pilot'), false);
  assert.equal(joins, 1);
  response.resolve('player-1');
  assert.equal(await first, true);
  await Promise.resolve();
  assert.equal(loadPlayerId(saved), 'player-1');
  assert.equal(controller.getSnapshot().portfolio?.nickname, 'Pilot');
  assert.equal(await controller.join('Another'), false);
  assert.equal(joins, 1);
});

test('delayed portfolio reads cannot overwrite a completed trade, and duplicate orders are blocked', async () => {
  const oldRead = deferred<Portfolio>();
  const write = deferred<Portfolio>();
  let reads = 0;
  let writes = 0;
  const { controller } = await restored({
    portfolio: async () => { reads += 1; return reads === 1 ? portfolio() : oldRead.promise; },
    trade: () => { writes += 1; return write.promise; },
  });
  const refreshing = controller.refresh();
  const trading = controller.trade('star-1', 'buy', 1);
  assert.equal(await controller.trade('star-1', 'buy', 1), false);
  assert.equal(writes, 1);
  write.resolve(portfolio(900, 1));
  assert.equal(await trading, true);
  oldRead.resolve(portfolio());
  await refreshing;
  assert.equal(controller.getSnapshot().portfolio?.cash, 900);
  assert.equal(controller.getSnapshot().portfolio?.holdings['star-1'], 1);
});

test('uncertain trades remain locked through failed refresh and unlock only after authoritative recovery', async () => {
  let reads = 0;
  let writes = 0;
  const { controller } = await restored({
    portfolio: async () => {
      reads += 1;
      if (reads === 2) throw new PlayerApiError('Temporarily unavailable');
      return reads === 1 ? portfolio() : portfolio(900, 1);
    },
    trade: async () => { writes += 1; throw new PlayerApiError('Lost response', undefined, true); },
  });
  assert.equal(await controller.trade('star-1', 'buy', 1), false);
  assert.equal(controller.getSnapshot().stale, true);
  assert.match(controller.getSnapshot().error ?? '', /outcome is uncertain/);
  assert.equal(await controller.trade('star-1', 'buy', 1), false);
  await controller.refresh();
  assert.equal(controller.getSnapshot().stale, true);
  assert.equal(writes, 1);
  await controller.refresh();
  assert.equal(controller.getSnapshot().stale, false);
  assert.equal(controller.getSnapshot().portfolio?.cash, 900);
  assert.equal(controller.getSnapshot().error, null);
  assert.match(controller.getSnapshot().notice ?? '', /Check your holdings and cash/);
});

test('temporary restore failures retain identity; a 404 after reconnect clears it without creating a replacement', async () => {
  let reads = 0;
  let joins = 0;
  const saved = storage('player-1');
  const controller = new PlayerSessionController(api({
    join: async () => { joins += 1; return 'new'; },
    portfolio: async () => {
      reads += 1;
      if (reads === 1) throw new PlayerApiError('Offline');
      throw new PlayerApiError('Player not found', 404);
    },
  }), saved);
  controller.setLive(true);
  await Promise.resolve();
  assert.equal(controller.getSnapshot().hasSession, true);
  assert.equal(loadPlayerId(saved), 'player-1');
  controller.setLive(false);
  controller.setLive(true);
  await Promise.resolve();
  assert.equal(controller.getSnapshot().hasSession, false);
  assert.equal(controller.getSnapshot().portfolio, undefined);
  assert.equal(loadPlayerId(saved), undefined);
  assert.equal(joins, 0);
  assert.match(controller.getSnapshot().notice ?? '', /restarted/);
});

test('disconnect disables trades and reconnect refreshes holdings before enabling them', async () => {
  const recovery = deferred<Portfolio>();
  let reads = 0;
  const { controller } = await restored({ portfolio: async () => ++reads === 1 ? portfolio() : recovery.promise });
  controller.setLive(false);
  assert.equal(controller.getSnapshot().stale, true);
  assert.equal(await controller.trade('star-1', 'buy', 1), false);
  controller.setLive(true);
  assert.equal(controller.getSnapshot().syncing, true);
  assert.equal(await controller.trade('star-1', 'buy', 1), false);
  recovery.resolve(portfolio(900, 1));
  await recovery.promise;
  await Promise.resolve();
  assert.equal(controller.getSnapshot().stale, false);
});

test('cleanup aborts portfolio reads and ignores their late results', async () => {
  const response = deferred<Portfolio>();
  let signal: AbortSignal | undefined;
  const controller = new PlayerSessionController(api({ portfolio: (_id, requestSignal) => {
    signal = requestSignal;
    return response.promise;
  } }), storage('player-1'));
  controller.setLive(true);
  controller.pause();
  assert.equal(signal?.aborted, true);
  response.resolve(portfolio(1, 100));
  await response.promise;
  assert.equal(controller.getSnapshot().portfolio, undefined);
  assert.equal(controller.getSnapshot().stale, true);
  assert.equal(controller.getSnapshot().syncing, false);
});

test('a rejected order preserves current balances; missing-player orders verify and reset the session', async () => {
  let missing = false;
  const { controller, saved } = await restored({
    portfolio: async () => {
      if (missing) throw new PlayerApiError('Player not found', 404);
      return portfolio();
    },
    trade: async () => {
      if (missing) throw new PlayerApiError('Player not found', 404);
      throw new PlayerApiError('Not enough cash', 400);
    },
  });
  assert.equal(await controller.trade('star-1', 'buy', 1), false);
  assert.equal(controller.getSnapshot().stale, false);
  assert.equal(controller.getSnapshot().portfolio?.cash, 1000);
  assert.equal(controller.getSnapshot().error, 'Not enough cash');
  missing = true;
  assert.equal(await controller.trade('star-1', 'buy', 1), false);
  await Promise.resolve();
  assert.equal(controller.getSnapshot().hasSession, false);
  assert.equal(loadPlayerId(saved), undefined);
});

test('an HTTP cash rejection leaves the account usable for a subsequent affordable buy', async () => {
  const requests: unknown[] = [];
  const initial = portfolio();
  const filled = portfolio(949.99, 0.5);
  const client = createPlayerApi({ fetch: async (url, init) => {
    assert.equal(String(url), '/trade');
    requests.push(JSON.parse(String(init?.body)));
    return requests.length === 1
      ? Response.json({ detail: 'Not enough cash: the final execution cost is 1,010.00' }, { status: 400 })
      : Response.json(filled);
  } });
  const { controller } = await restored({ trade: client.trade });

  assert.equal(await controller.trade('star-1', 'buy', 10), false);
  const rejected = controller.getSnapshot();
  assert.deepEqual(rejected.portfolio, initial);
  assert.equal(rejected.busy, null);
  assert.equal(rejected.stale, false);
  assert.match(rejected.error ?? '', /Not enough cash/);
  assert.equal(requests.length, 1, 'A rejected order must not be retried automatically.');

  assert.equal(await controller.trade('star-1', 'buy', 0.5), true);
  const recovered = controller.getSnapshot();
  assert.deepEqual(recovered.portfolio, filled);
  assert.equal(recovered.busy, null);
  assert.equal(recovered.stale, false);
  assert.equal(recovered.error, null);
  assert.deepEqual(requests, [
    { player_id: 'player-1', asset_id: 'star-1', side: 'buy', qty: 10 },
    { player_id: 'player-1', asset_id: 'star-1', side: 'buy', qty: 0.5 },
  ]);
});

test('polls share a slow portfolio request instead of repeatedly cancelling it', async () => {
  const response = deferred<Portfolio>();
  let requests = 0;
  let signal: AbortSignal | undefined;
  const controller = new PlayerSessionController(api({ portfolio: (_id, requestSignal) => {
    requests += 1;
    signal = requestSignal;
    return response.promise;
  } }), storage('player-1'));
  controller.setLive(true);
  // Simulate the next polling interval and a manual refresh while the read is pending.
  await controller.refresh();
  await controller.refresh();
  assert.equal(requests, 1);
  assert.equal(signal?.aborted, false);
  assert.equal(controller.getSnapshot().syncing, true);
  response.resolve(portfolio(750, 2.5));
  await response.promise;
  assert.equal(controller.getSnapshot().syncing, false);
  assert.equal(controller.getSnapshot().stale, false);
  assert.equal(controller.getSnapshot().portfolio?.cash, 750);
});

test('ordinary polling preserves trade rejection details until another action starts', async () => {
  const nextTrade = deferred<Portfolio>();
  let writes = 0;
  const { controller } = await restored({ trade: async () => {
    writes += 1;
    if (writes === 1) throw new PlayerApiError('Not enough cash', 400);
    return nextTrade.promise;
  } });
  await controller.trade('star-1', 'buy', 100);
  await controller.refresh();
  await controller.refresh();
  assert.equal(controller.getSnapshot().error, 'Not enough cash');
  const trade = controller.trade('star-1', 'buy', 0.25);
  assert.equal(controller.getSnapshot().error, null);
  nextTrade.resolve(portfolio(975, 0.25));
  assert.equal(await trade, true);
  assert.equal(controller.getSnapshot().error, null);
});

test('a pre-reconnect trade response cannot refresh balances before a new authoritative GET', async () => {
  const write = deferred<Portfolio>();
  const recovery = deferred<Portfolio>();
  let reads = 0;
  let writes = 0;
  const { controller } = await restored({
    portfolio: async () => ++reads === 1 ? portfolio() : recovery.promise,
    trade: () => { writes += 1; return write.promise; },
  });
  const trade = controller.trade('star-1', 'buy', 1);
  controller.setLive(false);
  controller.setLive(true);
  assert.equal(reads, 1);
  write.resolve(portfolio(900, 1));
  assert.equal(await trade, true);
  assert.equal(reads, 2);
  assert.equal(controller.getSnapshot().portfolio?.cash, 1000);
  assert.equal(controller.getSnapshot().stale, true);
  assert.equal(controller.getSnapshot().syncing, true);
  assert.equal(await controller.trade('star-1', 'buy', 1), false);
  assert.equal(writes, 1);
  recovery.resolve(portfolio(800, 2));
  await recovery.promise;
  await Promise.resolve();
  assert.equal(controller.getSnapshot().portfolio?.cash, 800);
  assert.equal(controller.getSnapshot().stale, false);
  assert.equal(controller.getSnapshot().error, null);
});

test('a restarted server clears the player even when an older trade succeeds after reconnect', async () => {
  const write = deferred<Portfolio>();
  let reads = 0;
  const { controller, saved } = await restored({
    portfolio: async () => {
      reads += 1;
      if (reads > 1) throw new PlayerApiError('Player not found', 404);
      return portfolio();
    },
    trade: () => write.promise,
  });
  const trade = controller.trade('star-1', 'buy', 1);
  controller.setLive(false);
  controller.setLive(true);
  write.resolve(portfolio(900, 1));
  await trade;
  await Promise.resolve();
  assert.equal(reads, 2);
  assert.equal(controller.getSnapshot().hasSession, false);
  assert.equal(controller.getSnapshot().portfolio, undefined);
  assert.equal(loadPlayerId(saved), undefined);
});
