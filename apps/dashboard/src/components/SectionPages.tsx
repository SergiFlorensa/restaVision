import {
  Activity,
  Bell,
  Camera,
  ClipboardList,
  Clock3,
  Gauge,
  MessageSquareText,
  PlugZap,
  Settings,
  Users,
  Utensils,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { dashboardConfig, resolveCameraStreamUrl, resolveTableServiceAnalysisUrl } from "../config";
import { metrics, tables } from "../data/dashboard";
import type {
  DrawerKind,
  MetricCardData,
  SectionId,
  TableMapItem,
  TableServiceAnalysis,
} from "../types";
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
  const serviceAnalysis = useTableServiceAnalysis();
  const overviewMetrics = useMemo(() => buildLiveMetrics(serviceAnalysis), [serviceAnalysis]);

  return (
    <section className="dashboard-grid fade-in">
      <div className="camera-area">
        <CameraPanel
          onOpenSettings={() => onOpenDrawer("camera")}
          serviceAnalysis={serviceAnalysis}
          streamUrl={resolveCameraStreamUrl()}
        />
      </div>

      <div className="metrics-grid">
        {overviewMetrics.map((metric) => (
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
        <TableServiceCard analysis={serviceAnalysis} onOpen={() => onOpenDrawer("alerts")} />
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
          serviceAnalysis={null}
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

function TableServiceCard({
  analysis,
  onOpen,
}: {
  analysis: TableServiceAnalysis | null;
  onOpen: () => void;
}) {
  const alerts = analysis?.active_alerts ?? [];
  const events = analysis?.timeline_events ?? [];
  const latestEvents = events.slice(0, 5);
  const tableLabel = analysis ? formatTableId(analysis.table_id) : "Mesa sin datos";
  const objectTotal = analysis
    ? Object.values(analysis.object_counts).reduce((total, value) => total + value, 0)
    : 0;
  const checklist = buildTableChecklist(analysis);

  return (
    <div className="panel table-service-card">
      <div className="table-service-header">
        <div className="panel-title">
          <ClipboardList size={21} />
          <h2>{tableLabel}</h2>
        </div>
        <span className={analysis?.people_count ? "status-pill active" : "status-pill"}>
          {analysis ? stateLabel(analysis.state) : "Esperando c?mara"}
        </span>
      </div>

      <p className="table-service-summary">
        {analysis
          ? buildTableSummary(analysis)
          : "La ficha mostrar? todo lo relacionado con la mesa enfocada cuando llegue se?al."}
      </p>

      <div className="table-service-kpis">
        <div>
          <span>Clientes</span>
          <strong>{analysis?.people_count ?? 0}</strong>
        </div>
        <div>
          <span>Objetos</span>
          <strong>{objectTotal}</strong>
        </div>
        <div>
          <span>Tiempo</span>
          <strong>{formatCompactDuration(analysis?.seat_duration_seconds ?? 0)}</strong>
        </div>
        <div>
          <span>Avisos</span>
          <strong>{alerts.length}</strong>
        </div>
      </div>

      <div className="table-checklist">
        {checklist.map((item) => (
          <article className={item.ok ? "check-card ok" : "check-card warning"} key={item.label}>
            <Utensils size={16} />
            <div>
              <strong>{item.label}</strong>
              <span>{item.detail}</span>
            </div>
          </article>
        ))}
      </div>

      <div className="table-event-feed" aria-label={`Registro operativo de ${tableLabel}`}>
        <div className="event-feed-title">
          <MessageSquareText size={17} />
          <strong>Registro de mesa</strong>
        </div>

        {alerts.map((alert) => (
          <article className="service-message alert" key={alert.alert_id}>
            <span>{formatTime(alert.ts)}</span>
            <div>
              <strong>{alert.message}</strong>
              <small>{eventLabel(alert.alert_type)}</small>
            </div>
          </article>
        ))}

        {latestEvents.length > 0 ? (
          latestEvents.map((event) => (
            <article className="service-message" key={event.event_id}>
              <span>{formatTime(event.ts)}</span>
              <div>
                <strong>{event.message}</strong>
                <small>{eventLabel(event.event_type)}</small>
              </div>
            </article>
          ))
        ) : (
          <article className="service-message muted">
            <span>--:--</span>
            <div>
              <strong>Sin eventos registrados en esta mesa</strong>
              <small>Los cambios aparecer?n aqu? como mensajes ordenados.</small>
            </div>
          </article>
        )}
      </div>

      {analysis?.updated_at ? (
        <span className="table-service-footnote">
          ?ltima actualizaci?n: {formatTime(analysis.updated_at)}
        </span>
      ) : null}

      <button className="secondary-action" onClick={onOpen} type="button">
        Abrir registro completo
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

function useTableServiceAnalysis(): TableServiceAnalysis | null {
  const [analysis, setAnalysis] = useState<TableServiceAnalysis | null>(null);

  useEffect(() => {
    let active = true;
    const url = resolveTableServiceAnalysisUrl();

    async function fetchAnalysis() {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as TableServiceAnalysis;
        if (active) {
          setAnalysis(payload);
        }
      } catch {
        if (active) {
          setAnalysis(null);
        }
      }
    }

    void fetchAnalysis();
    const interval = window.setInterval(() => void fetchAnalysis(), 2000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  return analysis;
}

function buildLiveMetrics(analysis: TableServiceAnalysis | null): MetricCardData[] {
  if (!analysis) {
    return metrics;
  }

  const occupied = analysis.people_count > 0 ? 1 : 0;
  const objectTotal = Object.values(analysis.object_counts).reduce(
    (total, value) => total + value,
    0,
  );
  const activeAlerts = analysis.active_alerts.length;
  const seatedMinutes = Math.floor((analysis.seat_duration_seconds ?? 0) / 60);

  return metrics.map((metric) => {
    if (metric.id === "people") {
      return {
        ...metric,
        helper: `Mesa ${analysis.table_id} · ${analysis.state}`,
        value: String(analysis.people_count),
      };
    }
    if (metric.id === "occupied") {
      return {
        ...metric,
        helper: `${objectTotal} objetos detectados`,
        value: `${occupied} / 1`,
      };
    }
    if (metric.id === "time") {
      return {
        ...metric,
        helper: analysis.away_duration_seconds
          ? `Ausente ${formatDuration(analysis.away_duration_seconds)}`
          : "Tiempo sentado mesa actual",
        value: String(seatedMinutes),
      };
    }
    if (metric.id === "queue") {
      return {
        ...metric,
        helper: analysis.timeline_events[0]?.message ?? "Sin alertas de servicio",
        value: String(activeAlerts),
      };
    }
    return metric;
  });
}

function buildTableSummary(analysis: TableServiceAnalysis): string {
  if (analysis.state === "waiting_for_video") {
    return "Mesa preparada para recibir señal de cámara. Aún no hay análisis visual.";
  }
  if (analysis.people_count === 0) {
    return "No hay clientes detectados en esta mesa. Se mantiene en observación.";
  }
  const missingCount = Object.values(analysis.missing_items).reduce(
    (total, value) => total + value,
    0,
  );
  if (missingCount > 0) {
    return `${analysis.people_count} cliente(s) detectados. Faltan ${missingCount} elemento(s) de servicio según el criterio actual.`;
  }
  if (analysis.service_flags.food_served) {
    return `${analysis.people_count} cliente(s) detectados. La mesa tiene comida servida y no hay faltas críticas.`;
  }
  return `${analysis.people_count} cliente(s) detectados. Servicio de mesa sin incidencias críticas.`;
}

function buildTableChecklist(analysis: TableServiceAnalysis | null) {
  if (!analysis) {
    return [
      { label: "Platos", detail: "Esperando análisis de cámara", ok: true },
      { label: "Cubiertos", detail: "Esperando análisis de cámara", ok: true },
      { label: "Comida", detail: "Sin datos todavía", ok: true },
    ];
  }

  const missing = analysis.missing_items;
  const missingCutlery = ["fork", "knife", "spoon"]
    .filter((label) => (missing[label] ?? 0) > 0)
    .map((label) => `${labelName(label)}: ${missing[label]}`);

  return [
    {
      label: "Platos",
      detail:
        (missing.plate ?? 0) > 0
          ? `Faltan ${missing.plate} plato(s) según clientes detectados`
          : "Correcto según clientes detectados",
      ok: (missing.plate ?? 0) === 0,
    },
    {
      label: "Cubiertos",
      detail:
        missingCutlery.length > 0
          ? `Falta ${missingCutlery.join(", ")}`
          : "Cubiertos completos o no requeridos",
      ok: missingCutlery.length === 0,
    },
    {
      label: "Comida",
      detail: analysis.service_flags.food_served
        ? "Comida detectada en mesa"
        : "Sin comida detectada todavía",
      ok: true,
    },
  ];
}

function formatTableId(tableId: string): string {
  const match = tableId.match(/(\d+)$/);
  return match ? `Mesa ${Number(match[1])}` : tableId;
}

function stateLabel(state: string): string {
  const labels: Record<string, string> = {
    away: "Cliente ausente",
    eating: "Comiendo",
    empty: "Vacía",
    needs_setup: "Falta servicio",
    observing: "Observando",
    seated: "Sentado",
    waiting_for_video: "Sin vídeo",
  };
  return labels[state] ?? state;
}

function eventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    customer_attention_requested: "Posible llamada",
    customer_left_table: "Cliente se levanta",
    customer_returned: "Cliente vuelve",
    food_served: "Comida servida",
    missing_table_setup: "Servicio incompleto",
    plate_removed: "Retirada detectada",
    plate_served: "Plato detectado",
    table_session_started: "Inicio de mesa",
  };
  return labels[eventType] ?? eventType;
}

function labelName(label: string): string {
  const labels: Record<string, string> = {
    fork: "tenedor",
    knife: "cuchillo",
    plate: "plato",
    spoon: "cuchara",
  };
  return labels[label] ?? label;
}

function formatCompactDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) {
    return "0m";
  }
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--:--";
  }
  return date.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}
