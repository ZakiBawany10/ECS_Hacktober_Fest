import { useId } from 'react';
import type { Candle } from '../market/types';
import './CandleChart.css';

interface CandleChartProps {
  candles?: Candle[];
}

const PLOT = { left: 12, right: 690, top: 24, bottom: 258 };
const PRICE_FORMAT = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 6 });

function validCandle(candle: Candle): boolean {
  return [candle.time, candle.open, candle.high, candle.low, candle.close].every(Number.isFinite)
    && candle.high >= Math.max(candle.open, candle.close)
    && candle.low <= Math.min(candle.open, candle.close);
}

export default function CandleChart({ candles = [] }: CandleChartProps) {
  const titleId = useId();
  const points = candles.filter(validCandle).sort((a, b) => a.time - b.time).slice(-60);
  const latest = points.at(-1);
  const empty = points.length === 0;
  const low = empty ? 0 : Math.min(...points.map((candle) => candle.low));
  const high = empty ? 1 : Math.max(...points.map((candle) => candle.high));
  const padding = Math.max((high - low) * 0.12, Math.abs(high) * 0.005, 0.000001);
  const minimum = low - padding;
  const maximum = high + padding;
  const scaleY = (value: number) => PLOT.bottom - ((value - minimum) / (maximum - minimum)) * (PLOT.bottom - PLOT.top);
  const step = (PLOT.right - PLOT.left) / Math.max(points.length, 12);
  const candleWidth = Math.min(step * 0.52, 14);
  const xFor = (index: number) => PLOT.left + step * (index + 0.5);

  return (
    <section className="chart-panel" aria-labelledby={titleId}>
      <div className="chart-heading">
        <div>
          <p className="chart-overline">Price action</p>
          <h3 id={titleId}>Candlestick chart</h3>
        </div>
        <span className="chart-mode">OHLC</span>
      </div>

      <dl className="chart-ohlc">
        {(['open', 'high', 'low', 'close'] as const).map((key) => (
          <div key={key}>
            <dt>{key.charAt(0).toUpperCase()}</dt>
            <dd>{latest ? PRICE_FORMAT.format(latest[key]) : `{${key}}`}</dd>
          </div>
        ))}
      </dl>

      <div className="chart-plot">
        <svg
          className="chart-svg"
          viewBox="0 0 800 300"
          role="img"
          aria-label={empty ? 'Candlestick chart awaiting price history' : `${points.length} price candles, most recent close ${PRICE_FORMAT.format(latest!.close)}`}
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
                  const value = maximum - ((maximum - minimum) * row) / 4;
                  return <text key={row} x="706" y={scaleY(value) + 4}>{PRICE_FORMAT.format(value)}</text>;
                })}
              </g>
              <g>
                {points.map((candle, index) => {
                  const openY = scaleY(candle.open);
                  const closeY = scaleY(candle.close);
                  return (
                    <g key={`${candle.time}-${index}`} className={candle.close >= candle.open ? 'chart-candle chart-candle-up' : 'chart-candle chart-candle-down'}>
                      <title>{`Open ${PRICE_FORMAT.format(candle.open)}, high ${PRICE_FORMAT.format(candle.high)}, low ${PRICE_FORMAT.format(candle.low)}, close ${PRICE_FORMAT.format(candle.close)}`}</title>
                      <line x1={xFor(index)} x2={xFor(index)} y1={scaleY(candle.high)} y2={scaleY(candle.low)} />
                      <rect x={xFor(index) - candleWidth / 2} y={Math.min(openY, closeY)} width={candleWidth} height={Math.max(Math.abs(closeY - openY), 1.5)} rx="0.5" />
                    </g>
                  );
                })}
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
        <span className="chart-footer-label">OHLC</span>
      </div>
    </section>
  );
}
