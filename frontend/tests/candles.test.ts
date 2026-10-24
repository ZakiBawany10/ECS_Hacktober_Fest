import assert from 'node:assert/strict';
import test from 'node:test';
import { buildCandles, mergePricePoints } from '../src/market/candles.ts';
import type { PricePoint } from '../src/market/candles.ts';

test('merge sorts ticks and replaces duplicate observations with the latest incoming price', () => {
  assert.deepEqual(mergePricePoints(
    [{ t: 4, price: 20 }, { t: 0, price: 8 }, { t: 4, price: 21 }],
    [{ t: 8, price: 24 }, { t: 4, price: 22 }, { t: 4, price: 23 }],
  ), [{ t: 0, price: 8 }, { t: 4, price: 23 }, { t: 8, price: 24 }]);
});

test('merge retains the latest bounded history and accepts zero', () => {
  const existing = [{ t: 1, price: 1 }, { t: 3, price: 0 }];
  const incoming = [{ t: 0, price: 10 }, { t: 2, price: 2 }];
  assert.deepEqual(mergePricePoints(existing, incoming, 2), [{ t: 2, price: 2 }, { t: 3, price: 0 }]);
  assert.deepEqual(existing, [{ t: 1, price: 1 }, { t: 3, price: 0 }]);
  assert.equal(mergePricePoints([], Array.from({ length: 605 }, (_, t) => ({ t, price: t }))).length, 600);
});

test('invalid ticks and prices are ignored without replacing valid rows', () => {
  const malformed = [
    { t: -1, price: 4 }, { t: 0.5, price: 4 }, { t: Infinity, price: 4 },
    { t: Number.MAX_SAFE_INTEGER + 1, price: 4 }, { t: 1, price: NaN },
    { t: 1, price: -1 }, { t: 1, price: Infinity }, { t: '2', price: 4 },
    { t: 2, price: '4' }, null, {}, undefined,
  ] as unknown as PricePoint[];
  assert.deepEqual(mergePricePoints([{ t: 1, price: 0 }], malformed), [{ t: 1, price: 0 }]);
  assert.deepEqual(buildCandles(malformed), []);
});

test('candles use chronological OHLC with duplicate ticks resolved before aggregation', () => {
  assert.deepEqual(buildCandles([
    { t: 9, price: 12 }, { t: 1, price: 10 }, { t: 3, price: 15 },
    { t: 4, price: 7 }, { t: 9, price: 13 }, { t: 10, price: 18 },
  ]), [
    { time: 0, open: 10, high: 15, low: 7, close: 13 },
    { time: 10, open: 18, high: 18, low: 18, close: 18 },
  ]);
});

test('partial buckets and gaps retain their actual ticks without invented candles or volume', () => {
  assert.deepEqual(buildCandles([
    { t: 5, price: 0 }, { t: 6, price: 0 }, { t: 45, price: 4 },
  ]), [
    { time: 0, open: 0, high: 0, low: 0, close: 0 },
    { time: 40, open: 4, high: 4, low: 4, close: 4 },
  ]);
  assert.deepEqual(buildCandles([]), []);
  assert.deepEqual(buildCandles([{ t: 0, price: 0 }]), [{ time: 0, open: 0, high: 0, low: 0, close: 0 }]);
});

test('custom intervals aggregate at the requested tick boundary', () => {
  assert.deepEqual(buildCandles([{ t: 4, price: 2 }, { t: 5, price: 3 }], 5), [
    { time: 0, open: 2, high: 2, low: 2, close: 2 },
    { time: 5, open: 3, high: 3, low: 3, close: 3 },
  ]);
});

test('invalid limits and candle intervals are rejected', () => {
  for (const value of [0, -1, 1.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() => mergePricePoints([], [], value), RangeError);
    assert.throws(() => buildCandles([], value), RangeError);
  }
});
