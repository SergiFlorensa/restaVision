import { Expand, Minus, Plus, UsersRound } from "lucide-react";

import { tables } from "../data/dashboard";
import type { TableMapItem, TableServiceAnalysis, TableStatus } from "../types";

export const statusLabels: Record<TableStatus, string> = {
  free: "Libre",
  occupied: "Ocupada",
  finishing: "Finalizando",
  dirty: "Mesa sucia",
  cleaning: "Limpieza",
  releasing: "Por liberar",
  reserved: "Reservada",
  offline: "Fuera de servicio",
};

const legend: TableStatus[] = ["free", "occupied", "finishing", "dirty", "reserved", "offline"];

interface TableMapProps {
  compact?: boolean;
  onTableSelect?: (table: TableMapItem) => void;
  serviceAnalysis?: TableServiceAnalysis | null;
}

export function TableMap({ compact = false, onTableSelect, serviceAnalysis }: TableMapProps) {
  const liveTables = tables.map((table) => {
    if (!serviceAnalysis || table.id !== tableNumberFromId(serviceAnalysis.table_id)) {
      return table;
    }
    return {
      ...table,
      status: mapAnalysisStateToTableStatus(serviceAnalysis.state),
    };
  });

  return (
    <section className={compact ? "panel table-map-panel compact" : "panel table-map-panel"}>
      <header className="map-header">
        <div className="panel-title">
          <UsersRound size={21} />
          <h2>Mapa de Mesas</h2>
        </div>
        <div className="map-legend">
          {legend.map((status) => (
            <span key={status}>
              <i className={`status-dot ${status}`} />
              {statusLabels[status]}
            </span>
          ))}
        </div>
      </header>

      <div className="floor-plan" aria-label="Mapa operativo de mesas">
        <div className="kitchen-zone">Cocina</div>
        <div className="bar-zone" />
        <div className="entrance-zone" />
        <div className="floor-walkway" />
        {liveTables.map((table) => (
          <button
            aria-label={`Mesa ${table.id}: ${statusLabels[table.status]}`}
            className={`table-node ${table.status}`}
            key={table.id}
            onClick={() => onTableSelect?.(table)}
            style={{ left: `${table.x}%`, top: `${table.y}%` }}
            type="button"
          >
            {table.id}
          </button>
        ))}
      </div>

      <footer className="map-footer">
        <button className="room-select">Salón Principal</button>
        <div className="zoom-controls">
          <button aria-label="Alejar">
            <Minus size={18} />
          </button>
          <span>100%</span>
          <button aria-label="Acercar">
            <Plus size={18} />
          </button>
          <button aria-label="Expandir mapa">
            <Expand size={18} />
          </button>
        </div>
      </footer>
    </section>
  );
}

function tableNumberFromId(tableId: string): number | null {
  const match = tableId.match(/(\d+)$/);
  return match ? Number(match[1]) : null;
}

function mapAnalysisStateToTableStatus(state: string): TableStatus {
  if (state === "dirty") {
    return "dirty";
  }
  if (state === "finishing") {
    return "finishing";
  }
  if (state === "eating" || state === "needs_setup" || state === "seated") {
    return "occupied";
  }
  if (state === "away") {
    return "releasing";
  }
  return "free";
}
