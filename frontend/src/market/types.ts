/** Frontend view models. Map agreed backend messages into these at integration. */
export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type StarCategory = 'Main sequence' | 'Giant' | 'Remnant' | 'Nebula';

export interface StarAsset {
  id: string;
  symbol: string;
  name: string;
  category: StarCategory;
  classification: string;
  color: string;
  price: number;
  previousClose: number;
  previousPrice: number;
  history: Candle[];
  luminosity: number;
  radius: number;
  mass: number;
  description: string;
  signal: string;
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
  news: NewsHeadline[];
  updatedAt: number;
  tick: number;
}

export type CandleInterval = '1m' | '5m' | '15m';

export function percentageChange(asset: Pick<StarAsset, 'price' | 'previousClose'>): number {
  return asset.previousClose > 0 ? ((asset.price - asset.previousClose) / asset.previousClose) * 100 : 0;
}
