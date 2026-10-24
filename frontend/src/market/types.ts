/** Frontend view models. Map agreed backend messages into these at integration. */
export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export type StarCategory = 'Main sequence' | 'Giant' | 'Remnant' | 'Nebula';

export interface StarAsset {
  id: string;
  symbol: string;
  name: string;
  category: StarCategory;
  classification: string;
  stage: string;
  spectralType: string;
  temperature: number;
  color: string;
  price: number;
  previousPrice: number | null;
  previousChange?: number | null;
  history: Candle[];
  luminosity: number;
  radius?: number;
  mass: number;
  description?: string;
  signal?: string;
}

export type NewsCategory = 'Breaking' | 'Observation' | 'Signal' | 'Market';

export interface NewsHeadline {
  id: string;
  timestamp: number;
  category: NewsCategory;
  headline: string;
  body: string;
  assetId: string;
  impact: 'positive' | 'negative' | 'neutral';
}

export interface MarketView {
  assets: StarAsset[];
  news?: NewsHeadline[];
  updatedAt: number;
  tick: number;
}

export type CandleInterval = '1m' | '5m' | '15m';

export type MarketConnectionStatus = 'connecting' | 'live' | 'reconnecting' | 'offline';

/** Absolute credit change between observed server ticks, not a market-close return. */
export function priceChange(asset: Pick<StarAsset, 'price' | 'previousPrice'>): number | null {
  return asset.previousPrice === null ? null : asset.price - asset.previousPrice;
}
