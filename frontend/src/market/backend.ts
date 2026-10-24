import { buildCandles, mergePricePoints } from './candles.ts';
import type { PricePoint } from './candles.ts';
import { mergeNewsItems, parseNewsItem, parseNewsSnapshot } from './news.ts';
import type { MarketView, NewsHeadline, StarAsset, StarCategory } from './types.ts';

const stages = {
  main_sequence: { label: 'Main sequence', category: 'Main sequence' },
  red_giant: { label: 'Red giant', category: 'Giant', color: '#fb9277' },
  blue_giant: { label: 'Blue giant', category: 'Giant', color: '#a8c6ff' },
  red_hypergiant: { label: 'Red hypergiant', category: 'Giant', color: '#ff785f' },
  blue_hypergiant: { label: 'Blue hypergiant', category: 'Giant', color: '#80b0ff' },
  supernova: { label: 'Supernova', category: 'Remnant', color: '#f6e8ba' },
  planetary_nebula: { label: 'Planetary nebula', category: 'Nebula', color: '#b397ef' },
  white_dwarf: { label: 'White dwarf', category: 'Remnant', color: '#dbe8ff' },
  neutron_star: { label: 'Neutron star', category: 'Remnant', color: '#85d9e7' },
  black_hole: { label: 'Black hole', category: 'Remnant', color: '#a498cf' },
} satisfies Record<string, { label: string; category: StarCategory; color?: string }>;

export type BackendStage = keyof typeof stages;

export interface BackendAsset {
  id: string;
  name: string;
  kind: 'star';
  stage: BackendStage;
  spectral_type: string;
  mass: number;
  temperature: number;
  L: number;
  price: number;
  shares_total: number;
  shares_available: number;
}

export interface BackendSnapshot {
  t: number;
  assets: BackendAsset[];
  news?: NewsHeadline[];
  newsError?: string;
}

export interface BackendTick {
  type: 'tick';
  t: number;
  assets: Array<Pick<BackendAsset, 'id' | 'stage' | 'price' | 'L'>>;
}

export interface BackendNewsMessage {
  type: 'news';
  item: NewsHeadline;
}

export type BackendMarketMessage = BackendTick | BackendNewsMessage;

export interface LiveMarketState {
  market: MarketView;
  pointsByAsset: ReadonlyMap<string, PricePoint[]>;
  snapshotTick: number;
}

function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`Invalid ${label}: expected an object.`);
  }
  return value as Record<string, unknown>;
}

function string(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new Error(`Invalid ${label}: expected text.`);
  }
  return value;
}

function number(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    throw new Error(`Invalid ${label}: expected a nonnegative finite number.`);
  }
  return value;
}

function tick(value: unknown): number {
  const result = number(value, 'simulation tick');
  if (!Number.isSafeInteger(result)) throw new Error('Invalid simulation tick: expected an integer.');
  return result;
}

function stage(value: unknown): BackendStage {
  if (typeof value !== 'string' || !Object.hasOwn(stages, value)) {
    throw new Error('The server returned an unsupported stellar stage.');
  }
  return value as BackendStage;
}

function uniqueAssets<T extends { id: string }>(value: unknown, parse: (value: unknown) => T): T[] {
  if (!Array.isArray(value)) throw new Error('Invalid market assets: expected a list.');
  const assets = value.map(parse);
  if (new Set(assets.map((asset) => asset.id)).size !== assets.length) {
    throw new Error('The server returned duplicate asset IDs.');
  }
  return assets;
}

function parseAssetTick(value: unknown): BackendTick['assets'][number] {
  const asset = record(value, 'asset');
  return {
    id: string(asset.id, 'asset ID'),
    stage: stage(asset.stage),
    price: number(asset.price, 'price'),
    L: number(asset.L, 'luminosity'),
  };
}

export function parseSnapshot(value: unknown): BackendSnapshot {
  const snapshot = record(value, 'market snapshot');
  return {
    t: tick(snapshot.t),
    assets: uniqueAssets(snapshot.assets, (value) => {
      const asset = record(value, 'asset');
      if (asset.kind !== 'star') throw new Error('The server returned an unsupported asset kind.');
      return {
        ...parseAssetTick(asset),
        name: string(asset.name, 'asset name'),
        kind: 'star',
        spectral_type: string(asset.spectral_type, 'spectral type'),
        mass: number(asset.mass, 'mass'),
        temperature: number(asset.temperature, 'temperature'),
        shares_total: number(asset.shares_total, 'share supply'),
        shares_available: number(asset.shares_available, 'available shares'),
      };
    }),
    ...parseNewsSnapshot(snapshot.news),
  };
}

/** Compatibility helper for consumers interested only in stock ticks. */
export function parseTickMessage(value: unknown): BackendTick | null {
  const message = record(value, 'market message');
  if (message.type !== 'tick') return null;
  return { type: 'tick', t: tick(message.t), assets: uniqueAssets(message.assets, parseAssetTick) };
}

/** Ignore unrelated protocol messages while validating both supported streams. */
export function parseMarketMessage(value: unknown): BackendMarketMessage | null {
  const message = record(value, 'market message');
  if (message.type === 'news') return { type: 'news', item: parseNewsItem(message.item) };
  return parseTickMessage(message);
}

export function parseHistory(value: unknown): PricePoint[] {
  if (!Array.isArray(value)) throw new Error('Invalid price history: expected a list.');
  return value.map((value) => {
    const point = record(value, 'price history point');
    return { t: tick(point.t), price: number(point.price, 'historical price') };
  });
}

function appearance(stage: BackendStage, spectralType: string) {
  const metadata: { label: string; category: StarCategory; color?: string } = stages[stage];
  const spectralColors: Record<string, string> = {
    O: '#99b9ff', B: '#b4caff', A: '#dde6ff', F: '#f3ecd4',
    G: '#efd18b', K: '#f1ac78', M: '#ee8b7c',
  };
  return {
    stage,
    classification: metadata.label,
    category: metadata.category,
    color: metadata.color ?? spectralColors[spectralType[0]?.toUpperCase()] ?? '#bdc8e0',
  };
}

/** A new authoritative snapshot starts a fresh connection baseline and history. */
export function createMarketState(snapshot: BackendSnapshot, receivedAt = Date.now()): LiveMarketState {
  const pointsByAsset = new Map<string, PricePoint[]>();
  const assets = snapshot.assets.map((asset): StarAsset => {
    const points = [{ t: snapshot.t, price: asset.price }];
    pointsByAsset.set(asset.id, points);
    return {
      id: asset.id,
      symbol: asset.id,
      name: asset.name,
      ...appearance(asset.stage, asset.spectral_type),
      spectralType: asset.spectral_type,
      temperature: asset.temperature,
      price: asset.price,
      previousPrice: null,
      previousChange: null,
      luminosity: asset.L,
      mass: asset.mass,
      history: buildCandles(points),
    };
  });
  return {
    market: {
      assets, tick: snapshot.t, updatedAt: receivedAt,
      news: snapshot.news === undefined ? undefined : mergeNewsItems([], [...snapshot.news].reverse()),
      newsError: snapshot.newsError,
    },
    pointsByAsset,
    snapshotTick: snapshot.t,
  };
}

/** News has its own event tick and must never advance the market clock or prices. */
export function applyMarketMessage(
  state: LiveMarketState,
  message: BackendMarketMessage,
  receivedAt = Date.now(),
): LiveMarketState {
  if (message.type === 'tick') return applyMarketTick(state, message, receivedAt);
  const news = mergeNewsItems(state.market.news ?? [], [message.item]);
  if (state.market.news?.length === news.length && news.every((item, index) => item === state.market.news?.[index])) {
    return state;
  }
  return {
    ...state,
    market: {
      ...state.market,
      news,
    },
  };
}

/** Ignore duplicate/out-of-order frames so prices and history never move backwards. */
export function applyMarketTick(
  state: LiveMarketState,
  message: BackendTick,
  receivedAt = Date.now(),
): LiveMarketState {
  if (message.t <= state.market.tick) return state;
  const updates = new Map(message.assets.map((asset) => [asset.id, asset]));
  if (message.assets.some((asset) => !state.pointsByAsset.has(asset.id))) {
    throw new Error('The market asset list changed. A fresh snapshot is required.');
  }
  const pointsByAsset = new Map(state.pointsByAsset);
  const assets = state.market.assets.map((asset) => {
    const update = updates.get(asset.id);
    if (!update) return asset;
    const points = mergePricePoints(pointsByAsset.get(asset.id) ?? [], [{ t: message.t, price: update.price }]);
    pointsByAsset.set(asset.id, points);
    return {
      ...asset,
      ...appearance(update.stage, asset.spectralType),
      previousPrice: asset.price,
      previousChange: asset.previousPrice === null ? null : asset.price - asset.previousPrice,
      price: update.price,
      luminosity: update.L,
      history: buildCandles(points),
    };
  });
  return {
    ...state,
    market: { ...state.market, assets, tick: message.t, updatedAt: receivedAt },
    pointsByAsset,
  };
}

/** Late HTTP history cannot overwrite a price already observed on this connection. */
export function mergeAssetHistory(state: LiveMarketState, assetId: string, history: PricePoint[]): LiveMarketState {
  if (!state.pointsByAsset.has(assetId)) return state;
  const latestTick = history.reduce((latest, point) => Math.max(latest, point.t), -1);
  if (latestTick < state.snapshotTick) {
    throw new Error('The server restarted while price history was loading.');
  }
  const points = mergePricePoints(
    history.filter((point) => point.t <= state.market.tick),
    state.pointsByAsset.get(assetId) ?? [],
  );
  const pointsByAsset = new Map(state.pointsByAsset);
  pointsByAsset.set(assetId, points);
  return {
    ...state,
    pointsByAsset,
    market: {
      ...state.market,
      assets: state.market.assets.map((asset) => asset.id === assetId ? { ...asset, history: buildCandles(points) } : asset),
    },
  };
}
