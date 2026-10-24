import type { Candle, NewsHeadline, NewsKind } from './types';

export interface ChartNewsMarker {
  id: string;
  /** The earliest actual news tick in this group, used for chart placement. */
  tick: number;
  endTick: number;
  kind: NewsKind | 'mixed';
  items: NewsHeadline[];
}

interface ChartNewsOptions {
  bucketTicks?: number;
  currentTick?: number;
  /** Merge nearby candle groups when their interactive targets would overlap. */
  minimumTickGap?: number;
}

export function visibleCandles(candles: readonly Candle[]): Candle[] {
  return candles.filter((candle) => (
    [candle.time, candle.open, candle.high, candle.low, candle.close].every(Number.isFinite)
    && Number.isSafeInteger(candle.time) && candle.time >= 0
    && Math.min(candle.open, candle.high, candle.low, candle.close) >= 0
    && candle.high >= Math.max(candle.open, candle.close)
    && candle.low <= Math.min(candle.open, candle.close)
  )).sort((a, b) => a.time - b.time).slice(-60);
}

/** Group received stories within the visible price window, without inventing event ticks. */
export function groupChartNews(
  candles: readonly Candle[],
  news: readonly NewsHeadline[],
  { bucketTicks = 10, currentTick, minimumTickGap = 0 }: ChartNewsOptions = {},
): ChartNewsMarker[] {
  if (!Number.isSafeInteger(bucketTicks) || bucketTicks <= 0) {
    throw new RangeError('Candle interval must be a positive safe integer');
  }
  if (!Number.isFinite(minimumTickGap) || minimumTickGap < 0) {
    throw new RangeError('Minimum marker gap must be finite and nonnegative');
  }

  const points = visibleCandles(candles);
  if (points.length === 0) return [];
  const firstTick = points[0].time;
  const windowEnd = Math.min(Number.MAX_SAFE_INTEGER, points.at(-1)!.time + bucketTicks - 1);
  const lastTick = currentTick !== undefined && Number.isSafeInteger(currentTick) && currentTick >= 0
    ? Math.min(windowEnd, currentTick)
    : windowEnd;

  // A repeated ID describes one received story; the latest version wins before window clipping.
  const byId = new Map<string, NewsHeadline>();
  for (const item of news) {
    if (typeof item.id === 'string' && item.id.trim().length > 0
      && Number.isSafeInteger(item.tick) && item.tick >= 0) byId.set(item.id, item);
  }
  const stories = [...byId.values()]
    .filter((item) => item.tick >= firstTick && item.tick <= lastTick)
    .sort((a, b) => a.tick - b.tick || a.id.localeCompare(b.id));

  const groups: ChartNewsMarker[] = [];
  for (const item of stories) {
    const bucket = Math.floor(item.tick / bucketTicks) * bucketTicks;
    const previous = groups.at(-1);
    const sameBucket = previous !== undefined
      && Math.floor(previous.endTick / bucketTicks) * bucketTicks === bucket;
    if (previous && (sameBucket || item.tick - previous.tick < minimumTickGap)) {
      previous.items.push(item);
      previous.endTick = item.tick;
      if (previous.kind !== item.kind) previous.kind = 'mixed';
    } else {
      groups.push({
        id: `news-bucket-${bucket}`,
        tick: item.tick,
        endTick: item.tick,
        kind: item.kind,
        items: [item],
      });
    }
  }
  return groups;
}
