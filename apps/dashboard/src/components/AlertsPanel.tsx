import { Bell, ChevronRight } from "lucide-react";

import { alerts } from "../data/dashboard";

interface AlertsPanelProps {
  onOpenAll: () => void;
}

export function AlertsPanel({ onOpenAll }: AlertsPanelProps) {
  return (
    <section className="panel alerts-panel">
      <header className="panel-title">
        <Bell size={21} />
        <h2>Avisos e Indicaciones</h2>
      </header>

      {alerts.length > 0 ? (
        <div className="alert-list">
          {alerts.map((alert) => (
            <article className={`alert-item ${alert.tone}`} key={alert.id}>
              <div className="alert-icon">
                <Bell size={16} />
              </div>
              <div>
                <strong>{alert.title}</strong>
                <span>{alert.description}</span>
              </div>
              <time>{alert.time}</time>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-panel small">
          <strong>Sin avisos activos</strong>
          <span>Las indicaciones aparecerán aquí cuando el backend genere eventos.</span>
        </div>
      )}

      <button className="secondary-action" onClick={onOpenAll} type="button">
        Ver todas las alertas
        <ChevronRight size={18} />
      </button>
    </section>
  );
}
