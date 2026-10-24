import assert from 'node:assert/strict';
import test from 'node:test';
import { groupChartNews, visibleCandles } from '../src/market/chartNews.ts';
import type { Candle, NewsHeadline } from '../src/market/types.ts';

const candle = (time: number): Candle => ({ time, open: 10, high: 12, low: 9, close: 11 });
const story = (id: string, tick: number, kind: NewsHeadline['kind'] = 'event'): NewsHeadline => ({
  id, tick, kind, headline: `Received headline ${id}`, body: '', assetIds: ['star-1'],
});

test('markers require price history and stay inside the last 60 visible candles', () => {
  assert.deepEqual(groupChartNews([], [story('a', 5)]), []);
  const candles = Array.from({ length: 64 }, (_, index) => candle(index * 10));
  const groups = groupChartNews(candles, [story('old', 39), story('first', 40), story('last', 639), story('future', 640)]);
  assert.deepEqual(groups.map((group) => [group.tick, group.items[0].id]), [[40, 'first'], [639, 'last']]);
  assert.equal(visibleCandles(candles).length, 60);
  assert.equal(candles.length, 64);
});

test('partial latest candles include the current tick but exclude unobserved future ticks', () => {
  const groups = groupChartNews([candle(10), candle(20)], [
    story('before', 9), story('start', 10), story('now', 23), story('later', 24), story('outside', 30),
  ], { currentTick: 23 });
  assert.deepEqual(groups.flatMap((group) => group.items.map((item) => item.id)), ['start', 'now']);
  assert.deepEqual(groupChartNews([candle(20)], [story('a', 20)], { currentTick: 19 }), []);
});

test('same candle stories retain their actual ticks and headline identities, including ties and late arrivals', () => {
  const groups = groupChartNews([candle(10), candle(20)], [
    story('later', 19), story('tie-b', 12), story('early', 11), story('tie-a', 12, 'lifecycle'),
  ]);
  assert.equal(groups.length, 1);
  assert.equal(groups[0].id, 'news-bucket-10');
  assert.equal(groups[0].tick, 11);
  assert.equal(groups[0].endTick, 19);
  assert.equal(groups[0].kind, 'mixed');
  assert.deepEqual(groups[0].items.map((item) => item.id), ['early', 'tie-a', 'tie-b', 'later']);
  assert.equal(groupChartNews([candle(10), candle(20), candle(30)], [story('later', 19)])[0].id, groups[0].id);
});

test('a repeated story ID is counted once and its latest version determines visible placement', () => {
  const updated = { ...story('same', 21), headline: 'Updated received headline' };
  const groups = groupChartNews([candle(10), candle(20)], [story('same', 12), updated, story('other', 21)]);
  assert.equal(groups.length, 1);
  assert.equal(groups[0].tick, 21);
  assert.equal(groups[0].items.length, 2);
  assert.equal(groups[0].items.find((item) => item.id === 'same')?.headline, updated.headline);
  assert.deepEqual(groupChartNews([candle(10)], [story('same', 12), story('same', 100)]), []);
});

test('nearby candle groups merge only when needed to keep markers apart', () => {
  const news = [story('a', 9), story('b', 10), story('c', 29), story('d', 30)];
  assert.equal(groupChartNews([candle(0), candle(30)], news).length, 4);
  const groups = groupChartNews([candle(0), candle(30)], news, { minimumTickGap: 20 });
  assert.deepEqual(groups.map((group) => [group.tick, group.items.map((item) => item.id)]), [
    [9, ['a', 'b']], [29, ['c', 'd']],
  ]);
  assert.equal(groups[1].tick - groups[0].tick, 20);
});

test('stories in a real history gap retain their tick without adding candles or inferred effects', () => {
  const candles = [candle(0), candle(40)];
  const received = story('gap', 25, 'rumour');
  const [group] = groupChartNews(candles, [received]);
  assert.equal(group.tick, 25);
  assert.equal(group.kind, 'rumour');
  assert.equal(group.items[0], received);
  assert.equal(candles.length, 2);
});

test('invalid story ticks and invalid price candles cannot create markers', () => {
  const news = [story('negative', -1), story('fraction', 1.5), story('infinite', Infinity), story('', 1), story('valid', 1)];
  assert.deepEqual(groupChartNews([candle(0)], news).map((group) => group.items[0].id), ['valid']);
  assert.deepEqual(groupChartNews([{ ...candle(0), high: 1 }], [story('valid', 1)]), []);
});

test('custom candle intervals preserve their boundaries and invalid options are rejected', () => {
  const groups = groupChartNews([candle(5), candle(10)], [story('a', 9), story('b', 10), story('c', 15)], { bucketTicks: 5 });
  assert.deepEqual(groups.map((group) => group.tick), [9, 10]);
  for (const bucketTicks of [0, -1, 1.5, Infinity]) {
    assert.throws(() => groupChartNews([], [], { bucketTicks }), RangeError);
  }
  for (const minimumTickGap of [-1, Infinity, NaN]) {
    assert.throws(() => groupChartNews([], [], { minimumTickGap }), RangeError);
  }
});
