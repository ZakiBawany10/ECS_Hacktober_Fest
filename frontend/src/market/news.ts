import type { NewsHeadline, NewsKind } from './types.ts';

export const NEWS_RETENTION = 50;

const newsKinds: readonly NewsKind[] = ['lifecycle', 'event', 'rumour', 'system'];

function sameNews(left: NewsHeadline, right: NewsHeadline): boolean {
  return left.id === right.id && left.tick === right.tick && left.kind === right.kind
    && left.headline === right.headline && left.body === right.body
    && left.assetIds.length === right.assetIds.length
    && left.assetIds.every((id, index) => id === right.assetIds[index]);
}

function text(value: unknown, label: string, allowEmpty = false): string {
  if (typeof value !== 'string' || (!allowEmpty && value.trim().length === 0)) {
    throw new Error(`Invalid news ${label}: expected text.`);
  }
  return value;
}

/** News ticks describe the event, and can arrive after newer market ticks. */
export function parseNewsItem(value: unknown): NewsHeadline {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Invalid news item: expected an object.');
  }
  const item = value as Record<string, unknown>;
  if (typeof item.t !== 'number' || !Number.isSafeInteger(item.t) || item.t < 0) {
    throw new Error('Invalid news tick: expected a nonnegative integer.');
  }
  if (typeof item.kind !== 'string' || !newsKinds.includes(item.kind as NewsKind)) {
    throw new Error('Invalid news kind: unsupported category.');
  }
  if (!Array.isArray(item.asset_ids)) {
    throw new Error('Invalid news asset IDs: expected a list.');
  }
  const assetIds = item.asset_ids.map((id) => text(id, 'asset ID'));
  if (new Set(assetIds).size !== assetIds.length) {
    throw new Error('Invalid news asset IDs: duplicate IDs.');
  }
  return {
    id: text(item.id, 'ID'),
    tick: item.t,
    kind: item.kind as NewsKind,
    headline: text(item.headline, 'headline'),
    body: text(item.body, 'body', true),
    assetIds,
  };
}

/** Incoming items are in receipt order, oldest first, as in the server snapshot. */
export function mergeNewsItems(
  existing: readonly NewsHeadline[],
  incoming: readonly NewsHeadline[],
): NewsHeadline[] {
  const rows = new Map(existing.map((item, order) => [item.id, { item, order }]));
  let nextOrder = -1;
  for (const item of incoming) {
    const previous = rows.get(item.id);
    // A replay of an existing ID must not make it jump ahead of its neighbours.
    rows.set(item.id, {
      item: previous && sameNews(previous.item, item) ? previous.item : item,
      order: previous?.order ?? nextOrder--,
    });
  }
  return [...rows.values()]
    .sort((left, right) => right.item.tick - left.item.tick || left.order - right.order)
    .slice(0, NEWS_RETENTION)
    .map(({ item }) => item);
}

/** Invalid news cannot prevent valid stock prices from loading. */
export function parseNewsSnapshot(value: unknown): {
  news: NewsHeadline[] | undefined;
  newsError?: string;
} {
  if (!Array.isArray(value)) {
    return { news: undefined, newsError: 'The server did not provide a usable news feed.' };
  }
  const news: NewsHeadline[] = [];
  let rejected = 0;
  for (const item of value) {
    try {
      news.push(parseNewsItem(item));
    } catch {
      rejected += 1;
    }
  }
  return {
    news: mergeNewsItems([], news),
    ...(rejected > 0 ? { newsError: 'Some news items could not be loaded.' } : {}),
  };
}
