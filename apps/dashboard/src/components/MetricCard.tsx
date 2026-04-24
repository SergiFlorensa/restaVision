import type { MetricCardData } from "../types";

interface MetricCardProps {
  metric: MetricCardData;
  onOpen: () => void;
}

export function MetricCard({ metric, onOpen }: MetricCardProps) {
  const Icon = metric.icon;
  return (
    <button className="metric-card" onClick={onOpen} type="button">
      <div className={`metric-icon ${metric.tone}`}>
        <Icon size={24} strokeWidth={1.9} />
      </div>
      <p>{metric.label}</p>
      <div className="metric-value-row">
        <strong>{metric.value}</strong>
        {metric.suffix ? <span>{metric.suffix}</span> : null}
      </div>
      <small>{metric.helper}</small>
    </button>
  );
}
