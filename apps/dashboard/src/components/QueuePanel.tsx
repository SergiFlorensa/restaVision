import { ChevronRight, UsersRound } from "lucide-react";

import { queueSeries } from "../data/dashboard";

interface QueuePanelProps {
  onOpenDetail: () => void;
}

export function QueuePanel({ onOpenDetail }: QueuePanelProps) {
  const chartWidth = 360;
  const chartHeight = 150;
  const paddingX = 26;
  const paddingY = 16;
  const maxGroups = 15;
  const plotWidth = chartWidth - paddingX * 2;
  const plotHeight = chartHeight - paddingY * 2;
  const points = queueSeries.map((point, index) => {
    const x = paddingX + (index / (queueSeries.length - 1)) * plotWidth;
    const y = paddingY + plotHeight - (point.groups / maxGroups) * plotHeight;
    return { ...point, x, y };
  });
  const linePath = points.map((point) => `${point.x},${point.y}`).join(" ");
  const areaPath = `${paddingX},${chartHeight - paddingY} ${linePath} ${
    chartWidth - paddingX
  },${chartHeight - paddingY}`;

  return (
    <section className="panel queue-panel">
      <header className="panel-title">
        <UsersRound size={21} />
        <h2>Cola / Espera</h2>
      </header>

      <div className="queue-content">
        <div className="queue-stats">
          <div>
            <strong>0</strong>
            <span>Grupos en espera</span>
          </div>
          <div>
            <span>Tiempo estimado</span>
            <strong className="wine">0 min</strong>
          </div>
          <button onClick={onOpenDetail} type="button">
            Ver detalle de cola
            <ChevronRight size={18} />
          </button>
        </div>

        <div className="queue-chart">
          <svg aria-label="Evolución de grupos en cola" viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
            <defs>
              <linearGradient id="queueFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#8b1325" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#8b1325" stopOpacity="0.04" />
              </linearGradient>
            </defs>
            {[0, 5, 10, 15].map((tick) => {
              const y = paddingY + plotHeight - (tick / maxGroups) * plotHeight;
              return (
                <g key={tick}>
                  <line className="chart-grid" x1={paddingX} x2={chartWidth - paddingX} y1={y} y2={y} />
                  <text className="chart-label" x={0} y={y + 4}>
                    {tick}
                  </text>
                </g>
              );
            })}
            <polygon className="chart-area" points={areaPath} />
            <polyline className="chart-line" points={linePath} />
            {points
              .filter((_, index) => index % 3 === 0)
              .map((point) => (
                <text className="chart-time" key={point.time} x={point.x - 14} y={chartHeight - 2}>
                  {point.time}
                </text>
              ))}
          </svg>
        </div>
      </div>
    </section>
  );
}
