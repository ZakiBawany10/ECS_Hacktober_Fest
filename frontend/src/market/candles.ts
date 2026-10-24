import type { Candle } from './types';

export interface PricePoint {
  t: number;
  price: number;
}

function validPoint(point: PricePoint): boolean {
  return point !== null && typeof point === 'object'
    && Number.isSafeInteger(point.t) && point.t >= 0
    && Number.isFinite(point.price) && point.price >= 0;
}

function positiveInteger(value: number, label: string): void {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new RangeError(`${label} must be a positive safe integer`);
  }
}

/** Merge observed prices only. A newer observation replaces the same tick. */
export function mergePricePoints(
  existing: readonly PricePoint[],
  incoming: readonly PricePoint[],
  limit = 600,
): PricePoint[] {
  positiveInteger(limit, 'History limit');
  const byTick = new Map<number, PricePoint>();
  for (const point of [...existing, ...incoming]) {
    if (validPoint(point)) byTick.set(point.t, { t: point.t, price: point.price });
  }
  return [...byTick.values()].sort((a, b) => a.t - b.t).slice(-limit);
}

/** Aggregate actual observations into tick buckets, including partial buckets. */
export function buildCandles(points: readonly PricePoint[], bucketTicks = 10): Candle[] {
  positiveInteger(bucketTicks, 'Candle interval');
  const observations = mergePricePoints([], points, Math.max(points.length, 1));
  const candles: Candle[] = [];
  for (const point of observations) {
    const time = Math.floor(point.t / bucketTicks) * bucketTicks;
    const current = candles.at(-1);
    if (!current || current.time !== time) {
      candles.push({ time, open: point.price, high: point.price, low: point.price, close: point.price });
    } else {
      current.high = Math.max(current.high, point.price);
      current.low = Math.min(current.low, point.price);
      current.close = point.price;
    }
  }
  return candles;
}
