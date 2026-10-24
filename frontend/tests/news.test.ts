import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  applyMarketMessage,
  createMarketState,
  parseMarketMessage,
  parseSnapshot,
  parseTickMessage,
} from '../src/market/backend.ts';
import { mergeNewsItems, NEWS_RETENTION, parseNewsItem, parseNewsSnapshot } from '../src/market/news.ts';

function item(id = 'event-1', t = 5, extra: Record<string, unknown> = {}) {
  return { id, t, kind: 'lifecycle', headline: 'A real server headline', body: '', asset_ids: ['star-1'], ...extra };
}

function snapshot(news: unknown = [], t = 10) {
  return parseSnapshot({
    t,
    assets: [{
      id: 'star-1', name: 'Server star', kind: 'star', stage: 'main_sequence',
      spectral_type: 'G', mass: 1, temperature: 5800, L: 1, price: 500,
      shares_total: 1000, shares_available: 1000,
    }],
    news,
  });
}

function message(id: string, t: number, extra: Record<string, unknown> = {}) {
  const parsed = parseMarketMessage({ type: 'news', item: item(id, t, extra) });
  assert.ok(parsed);
  return parsed;
}

test('news maps real event ticks, categories and all related assets without fabricated metadata', () => {
  const parsed = parseNewsItem(item('id', 0, { asset_ids: ['star-1', 'star-2'] }));
  assert.deepEqual(parsed, {
    id: 'id', tick: 0, kind: 'lifecycle', headline: 'A real server headline', body: '',
    assetIds: ['star-1', 'star-2'],
  });
  assert.deepEqual(parseNewsItem(item('system-id', 2, { kind: 'system', asset_ids: [] })).assetIds, []);
});

test('every declared backend news kind is supported and unrelated socket messages stay ignored', () => {
  const newsroomSource = readFileSync(new URL('../../backend/app/newsroom.py', import.meta.url), 'utf8');
  const literal = newsroomSource.match(/^NewsKind\s*=\s*Literal\[([\s\S]*?)\]/m);
  assert.ok(literal, 'Backend must declare its NewsKind literal.');
  const kinds = [...literal[1].matchAll(/["']([^"']+)["']/g)].map((match) => match[1]);
  assert.ok(kinds.length > 0);
  for (const kind of kinds) assert.equal(parseNewsItem(item(kind, 4, { kind })).kind, kind);
  assert.equal(parseMarketMessage({ type: 'leaderboard', rows: [] }), null);
  assert.equal(parseTickMessage({ type: 'news', item: item() }), null);
});

test('oldest-first server snapshots become newest-event-first feeds, with newest receipt first for equal ticks', () => {
  const state = createMarketState(snapshot([
    item('older-tick', 2), item('equal-earlier', 8), item('equal-later', 8), item('delayed', 1),
  ]));
  assert.deepEqual(state.market.news?.map(({ id }) => id), ['equal-later', 'equal-earlier', 'older-tick', 'delayed']);
  const next = applyMarketMessage(state, message('equal-new', 8));
  assert.deepEqual(next.market.news?.map(({ id }) => id), ['equal-new', 'equal-later', 'equal-earlier', 'older-tick', 'delayed']);
});

test('buffered socket news overlaps a snapshot exactly once without moving replayed equal-tick neighbours', () => {
  const state = createMarketState(snapshot([item('first', 8), item('second', 8)]));
  let replayed = applyMarketMessage(state, message('first', 8));
  assert.equal(replayed, state);
  replayed = applyMarketMessage(replayed, message('second', 8));
  replayed = applyMarketMessage(replayed, message('new-after-snapshot', 9));
  replayed = applyMarketMessage(replayed, message('new-after-snapshot', 9));
  assert.deepEqual(replayed.market.news?.map(({ id }) => id), ['new-after-snapshot', 'second', 'first']);
  assert.equal(state.market.news?.length, 2);
});

test('delayed news is accepted independently from stock ticks without altering prices, history or freshness', () => {
  const state = createMarketState(snapshot([], 100), 1234);
  const next = applyMarketMessage(state, message('delayed', 2), 9999);
  assert.equal(next.market.tick, 100);
  assert.equal(next.market.updatedAt, 1234);
  assert.equal(next.market.assets, state.market.assets);
  assert.equal(next.pointsByAsset, state.pointsByAsset);
  assert.equal(next.snapshotTick, state.snapshotTick);
  assert.equal(next.market.news?.[0].tick, 2);

  const tick = parseMarketMessage({
    type: 'tick', t: 101, assets: [{ id: 'star-1', stage: 'main_sequence', price: 505, L: 1 }],
  });
  assert.ok(tick);
  const updated = applyMarketMessage(next, tick, 2000);
  assert.equal(updated.market.assets[0].price, 505);
  assert.equal(updated.market.updatedAt, 2000);
  assert.deepEqual(updated.market.news, next.market.news);
});

test('feed retention keeps the newest fifty event ticks even when delayed news arrives last', () => {
  const parsed = Array.from({ length: 70 }, (_, index) => parseNewsItem(item(`id-${index}`, index)));
  const feed = mergeNewsItems([], parsed);
  assert.equal(feed.length, NEWS_RETENTION);
  assert.equal(feed[0].tick, 69);
  assert.equal(feed.at(-1)?.tick, 20);
  const delayed = mergeNewsItems(feed, [parseNewsItem(item('very-delayed', 0))]);
  assert.deepEqual(delayed, feed);

  const tied = mergeNewsItems([], Array.from({ length: 60 }, (_, index) => parseNewsItem(item(`tie-${index}`, 4))));
  assert.equal(tied[0].id, 'tie-59');
  assert.equal(tied.at(-1)?.id, 'tie-10');
});

test('fresh snapshots replace old-session news even when the simulation restarts at a lower tick', () => {
  const previous = applyMarketMessage(createMarketState(snapshot([item('old', 999)], 1000)), message('old-late', 998));
  const restarted = createMarketState(snapshot([item('new-session', 0)], 0));
  assert.deepEqual(previous.market.news?.map(({ id }) => id), ['old', 'old-late']);
  assert.deepEqual(restarted.market.news?.map(({ id }) => id), ['new-session']);
  assert.equal(restarted.market.tick, 0);
  assert.deepEqual(createMarketState(snapshot([], 0)).market.news, []);
});

test('malformed or missing news stays isolated from valid prices and valid feed items', () => {
  for (const value of [null, {}, 'not-a-feed']) {
    const state = createMarketState(snapshot(value));
    assert.equal(state.market.assets[0].price, 500);
    assert.equal(state.market.news, undefined);
    assert.match(state.market.newsError ?? '', /usable news feed/);
  }
  const missing = snapshot();
  delete missing.news;
  const parsedMissing = parseSnapshot(missing);
  assert.equal(parsedMissing.news, undefined);
  assert.match(parsedMissing.newsError ?? '', /usable news feed/);

  const state = createMarketState(snapshot([item('valid'), { id: 'broken' }, item('valid-2', 7)]));
  assert.deepEqual(state.market.news?.map(({ id }) => id), ['valid-2', 'valid']);
  assert.match(state.market.newsError ?? '', /Some news items/);
  assert.equal(state.market.assets[0].price, 500);
  const later = applyMarketMessage(state, message('later', 11));
  assert.equal(later.market.newsError, state.market.newsError);
});

test('runtime validation rejects malformed news before it enters the feed', () => {
  const invalid: unknown[] = [
    null, [], 'headline', item('', 1), item('id', -1), item('id', 1.5), item('id', Infinity),
    item('id', 1, { t: '1' }), item('id', 1, { kind: 'breaking' }),
    item('id', 1, { headline: '  ' }), item('id', 1, { body: null }),
    item('id', 1, { asset_ids: 'star-1' }), item('id', 1, { asset_ids: [''] }),
    item('id', 1, { asset_ids: ['star-1', 'star-1'] }), item('id', 1, { asset_ids: [5] }),
  ];
  for (const value of invalid) {
    assert.throws(() => parseNewsItem(value), /Invalid news/);
    assert.throws(() => parseMarketMessage({ type: 'news', item: value }), /Invalid news/);
  }
  assert.deepEqual(parseNewsSnapshot([{}, null]).news, []);
});

test('duplicate IDs replace the payload while preserving order and never mutate input feeds', () => {
  const original = mergeNewsItems([], [parseNewsItem(item('a', 4)), parseNewsItem(item('b', 4))]);
  const replacement = parseNewsItem(item('a', 4, { body: 'Corrected server description' }));
  const next = mergeNewsItems(original, [replacement]);
  assert.deepEqual(next.map(({ id }) => id), ['b', 'a']);
  assert.equal(next[1].body, 'Corrected server description');
  assert.equal(original[1].body, '');
  assert.deepEqual(original.map(({ id }) => id), ['b', 'a']);
});
