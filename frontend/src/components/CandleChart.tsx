import { useEffect, useId, useRef, useState } from 'react';
import type { Candle, NewsHeadline } from '../market/types';
import { groupChartNews, visibleCandles } from '../market/chartNews';
import './CandleChart.css';

interface CandleChartProps {
  candles?: Candle[];
  bucketTicks?: number;
  news?: NewsHeadline[];
  currentTick?: number;
  activeNewsId?: string;
  onSelectNews?: (newsId: string) => void;
}

const PLOT = { left: 12, right: 690, top: 24, bottom: 258 };
const PRICE_FORMAT = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 6 });

function tickRange(first: number, last: number): string {
  return first === last ? `tick ${first}` : `ticks ${first}–${last}`;
}

export default function CandleChart({
  candles = [], bucketTicks = 10, news = [], currentTick, activeNewsId, onSelectNews,
}: CandleChartProps) {
  const titleId = useId();
  const newsListId = `${titleId}-news-list`;
  const plotRef = useRef<HTMLDivElement>(null);
  const markerButtons = useRef(new Map<string, HTMLButtonElement>());
  const [plotWidth, setPlotWidth] = useState(0);
  const [expandedStoryId, setExpandedStoryId] = useState<string | null>(null);
  const points = visibleCandles(candles);
  const latest = points.at(-1);
  const empty = points.length === 0;
  const low = empty ? 0 : Math.min(...points.map((candle) => candle.low));
  const high = empty ? 1 : Math.max(...points.map((candle) => candle.high));
  // Normalize before padding so even flat, zero, or very large prices have a finite scale.
  const normalizer = Math.max(high, 0.000001);
  const padding = Math.max((high - low) / normalizer * 0.12, high / normalizer * 0.005, 0.000001 / normalizer);
  const minimum = Math.max(0, low / normalizer - padding);
  const maximum = high / normalizer + padding;
  const scaleRatioY = (ratio: number) => PLOT.bottom - ((ratio - minimum) / (maximum - minimum)) * (PLOT.bottom - PLOT.top);
  const scaleY = (value: number) => scaleRatioY(value / normalizer);
  const firstTick = points[0]?.time ?? 0;
  const tickSpan = (latest?.time ?? firstTick) - firstTick + bucketTicks;
  const xAtTick = (tick: number) => PLOT.left + (tick - firstTick) / tickSpan * (PLOT.right - PLOT.left);
  const step = (PLOT.right - PLOT.left) * bucketTicks / tickSpan;
  const candleWidth = Math.min(step * 0.52, 14);
  const xFor = (candle: Candle) => xAtTick(candle.time + bucketTicks / 2);
  const markers = groupChartNews(points, news, {
    bucketTicks,
    currentTick,
    minimumTickGap: plotWidth > 0 ? 28 / plotWidth * 800 / (PLOT.right - PLOT.left) * tickSpan : 0,
  });
  const newsCount = markers.reduce((total, marker) => total + marker.items.length, 0);
  const expandedMarker = markers.find((marker) => marker.items.some((item) => item.id === expandedStoryId));

  useEffect(() => {
    const plot = plotRef.current;
    if (!plot) return;
    const measure = () => setPlotWidth(Math.max(0, plot.getBoundingClientRect().width - 24));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(plot);
    return () => observer.disconnect();
  }, []);

  return (
    <section className="chart-panel" aria-labelledby={titleId}>
      <div className="chart-heading">
        <div>
          <p className="chart-overline">Price action</p>
          <h3 id={titleId}>Candlestick chart</h3>
        </div>
        <span className="chart-mode">{bucketTicks} ticks / candle</span>
      </div>

      <dl className="chart-ohlc">
        {(['open', 'high', 'low', 'close'] as const).map((key) => (
          <div key={key}>
            <dt>{key.charAt(0).toUpperCase()}</dt>
            <dd>{latest ? PRICE_FORMAT.format(latest[key]) : `{${key}}`}</dd>
          </div>
        ))}
      </dl>

      <div className="chart-plot" ref={plotRef}>
        <svg
          className="chart-svg"
          viewBox="0 0 800 300"
          role="img"
          aria-label={empty ? 'Candlestick chart awaiting price history' : `${points.length} price candles grouped by ${bucketTicks} simulation ticks, most recent close ${PRICE_FORMAT.format(latest!.close)}`}
          preserveAspectRatio="none"
        >
          <g className="chart-grid">
            {[0, 1, 2, 3, 4].map((row) => {
              const y = PLOT.top + ((PLOT.bottom - PLOT.top) * row) / 4;
              return <line key={`horizontal-${row}`} x1={PLOT.left} x2={PLOT.right} y1={y} y2={y} />;
            })}
            {[0, 1, 2, 3, 4].map((column) => {
              const x = PLOT.left + ((PLOT.right - PLOT.left) * column) / 4;
              return <line key={`vertical-${column}`} x1={x} x2={x} y1={PLOT.top} y2={PLOT.bottom} />;
            })}
          </g>

          {!empty && (
            <>
              <g className="chart-axis-labels">
                {[0, 1, 2, 3, 4].map((row) => {
                  const ratio = maximum - ((maximum - minimum) * row) / 4;
                  const value = Math.min(Number.MAX_VALUE, ratio * normalizer);
                  return <text key={row} x="706" y={scaleRatioY(ratio) + 4}>{PRICE_FORMAT.format(value)}</text>;
                })}
                {[0, 1, 2, 3, 4].map((column) => {
                  const tick = firstTick + tickSpan * column / 4;
                  return <text key={`tick-${column}`} x={xAtTick(tick)} y="286" textAnchor={column === 0 ? 'start' : column === 4 ? 'end' : 'middle'}>{Math.round(tick)}</text>;
                })}
              </g>
              <g>
                {points.map((candle, index) => {
                  const openY = scaleY(candle.open);
                  const closeY = scaleY(candle.close);
                  return (
                    <g key={`${candle.time}-${index}`} className={candle.close >= candle.open ? 'chart-candle chart-candle-up' : 'chart-candle chart-candle-down'}>
                      <title>{`Tick ${candle.time}, open ${PRICE_FORMAT.format(candle.open)}, high ${PRICE_FORMAT.format(candle.high)}, low ${PRICE_FORMAT.format(candle.low)}, close ${PRICE_FORMAT.format(candle.close)}`}</title>
                      <line x1={xFor(candle)} x2={xFor(candle)} y1={scaleY(candle.high)} y2={scaleY(candle.low)} />
                      <rect x={xFor(candle) - candleWidth / 2} y={Math.min(openY, closeY)} width={candleWidth} height={Math.max(Math.abs(closeY - openY), 1.5)} rx="0.5" />
                    </g>
                  );
                })}
              </g>
              <g className="chart-news-guides" aria-hidden="true">
                {markers.map((marker) => (
                  <line key={marker.id} data-kind={marker.kind} x1={xAtTick(marker.tick)} x2={xAtTick(marker.tick)} y1="28" y2={PLOT.bottom} />
                ))}
              </g>
            </>
          )}

          {empty && (
            <g className="chart-axis-labels">
              <text x="706" y="145">{'{price}'}</text>
              <text x="12" y="286">{'{time}'}</text>
            </g>
          )}
        </svg>

        {markers.length > 0 && (
          <div className="chart-news-markers" role="group" aria-label="News on the price chart">
            {markers.map((marker) => {
              const selected = marker.items.some((item) => item.id === activeNewsId);
              const multiple = marker.items.length > 1;
              const expanded = expandedMarker?.id === marker.id;
              const label = multiple
                ? `${marker.items.length} news stories at ${tickRange(marker.tick, marker.endTick)}. Show headlines`
                : `${marker.items[0].headline}. Tick ${marker.tick}. Open news story`;
              return (
                <button
                  key={marker.id}
                  ref={(button) => {
                    if (button) markerButtons.current.set(marker.id, button);
                    else markerButtons.current.delete(marker.id);
                  }}
                  type="button"
                  className={`chart-news-marker${selected ? ' chart-news-marker-active' : ''}`}
                  style={{ left: `${xAtTick(marker.tick) / 8}%` }}
                  data-kind={marker.kind}
                  aria-label={label}
                  title={label}
                  aria-pressed={selected}
                  aria-expanded={multiple ? expanded : undefined}
                  aria-controls={multiple ? newsListId : undefined}
                  onClick={() => {
                    if (multiple || !onSelectNews) setExpandedStoryId(expanded ? null : marker.items[0].id);
                    else {
                      setExpandedStoryId(null);
                      onSelectNews(marker.items[0].id);
                    }
                  }}
                >
                  {multiple ? marker.items.length : (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                      <rect x="1.5" y="2" width="9" height="8" rx="1" stroke="currentColor" />
                      <path d="M3.5 4.5h5m-5 3h5" stroke="currentColor" />
                    </svg>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {empty && (
          <div className="chart-empty">
            <svg width="30" height="30" viewBox="0 0 30 30" fill="none" aria-hidden="true">
              <path d="M10 5v20m10-18v16" stroke="currentColor" strokeWidth="1.5" />
              <rect x="7" y="10" width="6" height="10" fill="var(--chart-surface, #171d1e)" stroke="currentColor" strokeWidth="1.5" />
              <rect x="17" y="12" width="6" height="6" fill="currentColor" />
            </svg>
            <span>{'{candlestick chart}'}</span>
          </div>
        )}
      </div>

      <div className="chart-footer">
        <span><i className="chart-legend-up" /> Rising</span>
        <span><i className="chart-legend-down" /> Falling</span>
        <span className="chart-footer-label">Simulation ticks</span>
      </div>
      {newsCount > 0 && (
        <div className="chart-news-caption">
          <span><i aria-hidden="true" /> {newsCount} news {newsCount === 1 ? 'story' : 'stories'}</span>
          <span>Select a marker to open news</span>
        </div>
      )}
      {expandedMarker && (
        <div className="chart-news-list" id={newsListId} role="region" aria-label={`News at ${tickRange(expandedMarker.tick, expandedMarker.endTick)}`}>
          <div className="chart-news-list-heading">
            <span>{expandedMarker.items.length} {expandedMarker.items.length === 1 ? 'headline' : 'headlines'} · {tickRange(expandedMarker.tick, expandedMarker.endTick)}</span>
            <button type="button" onClick={() => {
              setExpandedStoryId(null);
              markerButtons.current.get(expandedMarker.id)?.focus();
            }} aria-label="Close chart headlines">×</button>
          </div>
          <ul>
            {expandedMarker.items.map((item) => (
              <li key={item.id}>
                <button type="button" data-kind={item.kind} aria-pressed={item.id === activeNewsId} onClick={() => onSelectNews?.(item.id)}>
                  <span className="chart-news-story-tick">Tick {item.tick}</span>
                  <span>{item.headline}</span>
                  <span aria-hidden="true">↗</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
