import {
  Activity,
  Bell,
  Camera,
  Clock3,
  Gauge,
  PlugZap,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";

import { dashboardConfig, resolveCameraStreamUrl } from "../config";
import { metrics, tables } from "../data/dashboard";
import type { DrawerKind, SectionId, TableMapItem } from "../types";
import { CameraPanel } from "./CameraPanel";
import { MetricCard } from "./MetricCard";
import { QueuePanel } from "./QueuePanel";
import { TableMap } from "./TableMap";

interface SectionPagesProps {
  activeSection: SectionId;
  onOpenDrawer: (kind: DrawerKind) => void;
  onTableSelect: (table: TableMapItem) => void;
}

export function OverviewSection({ onOpenDrawer, onTableSelect }: Omit<SectionPagesProps, "activeSection">) {
  return (
    <section className="dashboard-grid fade-in">
      <div className="camera-area">
        <CameraPanel
          onOpenSettings={() => onOpenDrawer("camera")}
          streamUrl={resolveCameraStreamUrl()}
        />
      </div>

      <div className="metrics-grid">
        {metrics.map((metric) => (
          <MetricCard
            key={metric.id}
            metric={metric}
            onOpen={() => onOpenDrawer(metric.id === "queue" ? "queue" : "indicators")}
          />
        ))}
      </div>

      <div className="queue-area">
        <QueuePanel onOpenDetail={() => onOpenDrawer("queue")} />
      </div>

      <div className="map-area">
        <TableMap onTableSelect={onTableSelect} />
      </div>

      <div className="alerts-area">
        <AlertsSectionCard onOpen={() => onOpenDrawer("alerts")} />
      </div>
    </section>
  );
}

export function SectionPages({ activeSection, onOpenDrawer, onTableSelect }: SectionPagesProps) {
  if (activeSection === "overview") {
    return <OverviewSection onOpenDrawer={onOpenDrawer} onTableSelect={onTableSelect} />;
  }

  if (activeSection === "tables") {
    return (
      <section className="section-page fade-in">
        <TableMap compact onTableSelect={onTableSelect} />
        <OperationalPanel
          icon={Gauge}
          title="Estado de mesas"
          rows={[
            ["Mesas configuradas", `${tables.length}`],
            ["Ocupadas", "0"],
            ["Por liberar", "0"],
            ["Fuera de servicio", "0"],
          ]}
          onOpen={() => onOpenDrawer("tables")}
        />
      </section>
    );
  }

  if (activeSection === "cameras") {
    return (
      <section className="section-page fade-in">
        <CameraPanel
          onOpenSettings={() => onOpenDrawer("camera")}
          streamUrl={resolveCameraStreamUrl()}
        />
        <OperationalPanel
          icon={Camera}
          title="Cámara principal"
          rows={[
            ["Fuente", dashboardConfig.cameraStreamUrl || "Sin stream configurado"],
            ["Modo", "Webcam local o stream backend"],
            ["Overlays", "Pendientes de observaciones"],
          ]}
          onOpen={() => onOpenDrawer("camera")}
        />
      </section>
    );
  }

  if (activeSection === "people") {
    return (
      <SectionScaffold
        action={() => onOpenDrawer("people")}
        icon={Users}
        kpis={[
          ["Personas ahora", "0"],
          ["Entrada última hora", "0"],
          ["Salida última hora", "0"],
          ["Zonas activas", "0"],
        ]}
        title="Personas"
      />
    );
  }

  if (activeSection === "queue") {
    return (
      <section className="section-page fade-in">
        <QueuePanel onOpenDetail={() => onOpenDrawer("queue")} />
        <OperationalPanel
          icon={Bell}
          title="Reglas de cola"
          rows={[
            ["Grupos en espera", "0"],
            ["Aviso amarillo", ">= 4 grupos"],
            ["Aviso rojo", ">= 7 grupos"],
            ["Tiempo estimado", "0 min"],
          ]}
          onOpen={() => onOpenDrawer("queue")}
        />
      </section>
    );
  }

  if (activeSection === "indicators") {
    return (
      <SectionScaffold
        action={() => onOpenDrawer("indicators")}
        icon={Activity}
        kpis={[
          ["Ocupación", "0%"],
          ["Rotación", "0"],
          ["Tiempo medio", "0 min"],
          ["Salud pipeline", "Listo"],
        ]}
        title="Indicadores"
      />
    );
  }

  if (activeSection === "history") {
    return (
      <SectionScaffold
        action={() => onOpenDrawer("history")}
        icon={Clock3}
        kpis={[
          ["Eventos hoy", "0"],
          ["Sesiones cerradas", "0"],
          ["Alertas", "0"],
          ["Exportaciones", "0"],
        ]}
        title="Histórico"
      />
    );
  }

  return (
    <SectionScaffold
      action={() => onOpenDrawer("settings")}
      icon={Settings}
      kpis={[
        ["API", dashboardConfig.apiBaseUrl],
        ["Cámara", dashboardConfig.cameraStreamUrl ? "Configurada" : "Pendiente"],
        ["Tema", "Piemontesa"],
        ["Modo", "Local-first"],
      ]}
      title="Ajustes"
    />
  );
}

function AlertsSectionCard({ onOpen }: { onOpen: () => void }) {
  return (
    <div className="panel alerts-panel">
      <div className="panel-title">
        <Bell size={21} />
        <h2>Avisos e Indicaciones</h2>
      </div>
      <div className="empty-panel small">
        <strong>Sin avisos activos</strong>
        <span>Cuando conectes cámara y backend aparecerán aquí las indicaciones.</span>
      </div>
      <button className="secondary-action" onClick={onOpen} type="button">
        Configurar reglas de aviso
      </button>
    </div>
  );
}

function SectionScaffold({
  action,
  icon: Icon,
  kpis,
  title,
}: {
  action: () => void;
  icon: LucideIcon;
  kpis: Array<[string, string]>;
  title: string;
}) {
  return (
    <section className="section-page fade-in">
      <div className="panel section-hero">
        <div className="panel-title">
          <Icon size={24} />
          <h2>{title}</h2>
        </div>
        <p>
          Sección preparada para datos reales. Los valores arrancan a cero para evitar ruido visual
          antes de conectar cámara, backend y persistencia operativa.
        </p>
        <button className="primary-action inline" onClick={action} type="button">
          Configurar sección
        </button>
      </div>
      <div className="subsection-grid">
        {kpis.map(([label, value]) => (
          <article className="subsection-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </div>
      <div className="panel empty-state-wide">
        <PlugZap size={28} />
        <strong>Esperando datos del sistema</strong>
        <span>Esta zona se rellenará automáticamente cuando llegue información desde la API.</span>
      </div>
    </section>
  );
}

function OperationalPanel({
  icon: Icon,
  onOpen,
  rows,
  title,
}: {
  icon: LucideIcon;
  onOpen: () => void;
  rows: Array<[string, string]>;
  title: string;
}) {
  return (
    <aside className="panel operational-panel">
      <div className="panel-title">
        <Icon size={22} />
        <h2>{title}</h2>
      </div>
      <div className="operational-list">
        {rows.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <button className="primary-action inline" onClick={onOpen} type="button">
        Abrir ventana
      </button>
    </aside>
  );
}
