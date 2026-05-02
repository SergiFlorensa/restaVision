import {
  AlertTriangle,
  Activity,
  Bell,
  Camera,
  CheckCircle2,
  ClipboardList,
  Clock3,
  Gauge,
  ListChecks,
  MessageSquareText,
  PlugZap,
  RefreshCw,
  Settings,
  Timer,
  Users,
  Utensils,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  apiUrl,
  dashboardConfig,
  resolveCameraStreamUrl,
  resolveTableServiceAnalysisUrl,
  resolveTableServiceEventsUrl,
} from "../config";
import { tables } from "../data/dashboard";
import type {
  ApiTable,
  DecisionRecommendation,
  DrawerKind,
  QueueGroup,
  SectionId,
  TableMapItem,
  TableServiceAnalysis,
} from "../types";
import { CameraPanel } from "./CameraPanel";
import { CommandCenter } from "./CommandCenter";
import { QueuePanel } from "./QueuePanel";
import { TableMap } from "./TableMap";

interface SectionPagesProps {
  activeSection: SectionId;
  onOpenDrawer: (kind: DrawerKind) => void;
  onTableSelect: (table: TableMapItem) => void;
}

export function OverviewSection({ onOpenDrawer, onTableSelect }: Omit<SectionPagesProps, "activeSection">) {
  const serviceAnalysis = useTableServiceAnalysis();

  return (
    <section className="command-center-shell fade-in">
      <CommandCenter
        analysis={serviceAnalysis}
        onOpenAlerts={() => onOpenDrawer("alerts")}
        onOpenTableDetail={onTableSelect}
        onOpenTechnical={() => onOpenDrawer("camera")}
      />
    </section>
  );
}

export function OperationalCommandCenter({ onOpenTechnical }: { onOpenTechnical: () => void }) {
  const {
    decisions,
    error,
    loading,
    notice,
    queueGroups,
    refresh,
    registerFeedback,
    recordOperationalAction,
    tables: apiTables,
    createQueueGroup,
  } = useOperationalCopilot();
  const primary = decisions[0] ?? null;
  const pressureMode = primary?.mode ?? inferPressureMode(decisions, queueGroups);
  const waitingGroups = queueGroups.filter((group) => group.status === "waiting");
  const readyTables = apiTables.filter((table) => table.state === "ready").length;
  const focusTable = primary?.table_id
    ? apiTables.find((table) => table.table_id === primary.table_id)
    : apiTables[0];

  return (
    <div className="operation-command">
      <section className={`panel next-action-card ${priorityClass(primary?.priority)}`}>
        <div className="operation-eyebrow">
          <span className={`priority-badge ${priorityClass(primary?.priority)}`}>
            {primary?.priority ?? "P3"}
          </span>
          <span>{modeLabel(pressureMode)}</span>
          <button className="icon-action" onClick={refresh} title="Actualizar decisiones" type="button">
            <RefreshCw size={18} />
          </button>
        </div>

        <div className="next-action-body">
          <span className="next-action-label">Accion principal</span>
          <h2>{primary?.answer ?? "Sin accion critica ahora"}</h2>
          <p>
            {primary
              ? primary.reason.join(" · ")
              : "El sistema no ve una prioridad urgente. Mantener vigilancia de cola y mesas."}
          </p>
        </div>

        <div className="promise-strip">
          <div>
            <Timer size={18} />
            <span>Promesa</span>
            <strong>{primary?.eta_minutes != null ? `${primary.eta_minutes} min` : "--"}</strong>
          </div>
          <div>
            <Users size={18} />
            <span>Cola</span>
            <strong>{waitingGroups.length}</strong>
          </div>
          <div>
            <CheckCircle2 size={18} />
            <span>Listas</span>
            <strong>{readyTables}</strong>
          </div>
        </div>

        {primary ? (
          <div className="feedback-actions">
            <button
              className="primary-action"
              onClick={() => registerFeedback(primary.decision_id, true, true)}
              type="button"
            >
              Hecho
            </button>
            <button
              className="ghost-action"
              onClick={() => registerFeedback(primary.decision_id, false, null)}
              type="button"
            >
              Ignorar
            </button>
            <button
              className="ghost-action"
              onClick={() => registerFeedback(primary.decision_id, false, false)}
              type="button"
            >
              No util
            </button>
          </div>
        ) : null}
      </section>

      <section className="panel top-actions-panel">
        <div className="panel-title">
          <ListChecks size={21} />
          <h2>Top 3 acciones</h2>
        </div>
        <div className="top-action-list">
          {decisions.length > 0 ? (
            decisions.slice(0, 3).map((decision, index) => (
              <article className="top-action-item" key={decision.decision_id}>
                <span>{index + 1}</span>
                <div>
                  <strong>{decision.answer}</strong>
                  <small>{decision.reason.join(" · ") || decision.impact}</small>
                </div>
                <b className={priorityClass(decision.priority)}>{decision.priority}</b>
              </article>
            ))
          ) : (
            <article className="top-action-item muted">
              <span>0</span>
              <div>
                <strong>Sin acciones pendientes</strong>
                <small>{loading ? "Calculando..." : "Crea un grupo en cola para probar el flujo."}</small>
              </div>
            </article>
          )}
        </div>
      </section>

      <section className="panel queue-command-panel">
        <div className="panel-title">
          <Users size={21} />
          <h2>Cola activa</h2>
        </div>
        <div className="quick-party-actions">
          {[2, 4, 6].map((partySize) => (
            <button
              disabled={loading}
              key={partySize}
              onClick={() => createQueueGroup(partySize)}
              type="button"
            >
              Grupo {partySize}
            </button>
          ))}
        </div>
        {notice ? <p className="operation-notice">{notice}</p> : null}
        <div className="queue-group-list">
          {waitingGroups.slice(0, 4).map((group) => (
            <article key={group.queue_group_id}>
              <strong>Grupo {group.party_size}</strong>
              <span>{formatQueueWait(group.arrival_ts)}</span>
            </article>
          ))}
          {waitingGroups.length === 0 ? <span className="muted-line">Sin grupos esperando</span> : null}
        </div>
      </section>

      <section className="panel operation-status-panel">
        <div className="panel-title">
          <Gauge size={21} />
          <h2>Lectura rapida</h2>
        </div>
        <div className="status-rows">
          <div>
            <span>Mesas</span>
            <strong>{apiTables.length}</strong>
          </div>
          <div>
            <span>Ocupadas</span>
            <strong>{apiTables.filter((table) => table.state !== "ready").length}</strong>
          </div>
          <div>
            <span>Modo</span>
            <strong>{modeShortLabel(pressureMode)}</strong>
          </div>
        </div>
        {focusTable ? (
          <div className="table-action-strip">
            <span>{focusTable.name}</span>
            <button
              disabled={loading}
              onClick={() => recordOperationalAction("mark_needs_attention", focusTable.table_id)}
              type="button"
            >
              Revisar
            </button>
            <button
              disabled={loading}
              onClick={() => recordOperationalAction("request_bill", focusTable.table_id)}
              type="button"
            >
              Cuenta
            </button>
            <button
              disabled={loading}
              onClick={() => recordOperationalAction("cleaning_done", focusTable.table_id)}
              type="button"
            >
              Lista
            </button>
          </div>
        ) : null}
        {error ? (
          <p className="operation-error">
            <AlertTriangle size={16} />
            {error}
          </p>
        ) : (
          <button className="secondary-action" onClick={onOpenTechnical} type="button">
            Abrir modo tecnico
          </button>
        )}
      </section>
    </div>
  );
}

export function TechnicalSignalPanel({
  analysis,
  onOpenAlerts,
  onOpenCamera,
}: {
  analysis: TableServiceAnalysis | null;
  onOpenAlerts: () => void;
  onOpenCamera: () => void;
}) {
  return (
    <div className="technical-signal-stack">
      <section className="compact-camera-panel">
        <div className="panel-title">
          <Camera size={21} />
          <h2>Modo tecnico</h2>
        </div>
        <CameraPanel
          onOpenSettings={onOpenCamera}
          serviceAnalysis={analysis}
          streamUrl={resolveCameraStreamUrl()}
        />
      </section>
      <TableServiceCard analysis={analysis} onOpen={onOpenAlerts} />
    </div>
  );
}

function useOperationalCopilot() {
  const [decisions, setDecisions] = useState<DecisionRecommendation[]>([]);
  const [queueGroups, setQueueGroups] = useState<QueueGroup[]>([]);
  const [tables, setTables] = useState<ApiTable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(apiUrl(path), {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    if (!response.ok) {
      throw new Error(`API ${response.status}`);
    }
    return (await response.json()) as T;
  }

  async function refresh() {
    try {
      setLoading(true);
      const [nextTables, nextQueueGroups, nextDecisions] = await Promise.all([
        fetchJson<ApiTable[]>("/api/v1/tables"),
        fetchJson<QueueGroup[]>("/api/v1/queue/groups"),
        fetchJson<DecisionRecommendation[]>("/api/v1/decisions/next-best-action?limit=3"),
      ]);
      setTables(nextTables);
      setQueueGroups(nextQueueGroups);
      setDecisions(nextDecisions);
      setError(null);
    } catch {
      setError("No se pudo conectar con el copiloto operativo.");
    } finally {
      setLoading(false);
    }
  }

  async function createQueueGroup(partySize: number) {
    try {
      setLoading(true);
      await fetchJson<QueueGroup>("/api/v1/queue/groups", {
        method: "POST",
        body: JSON.stringify({ party_size: partySize }),
      });
      await refresh();
      setNotice(`Grupo de ${partySize} añadido. Recomendacion recalculada.`);
    } catch {
      setError("No se pudo crear el grupo en cola.");
    } finally {
      setLoading(false);
    }
  }

  async function registerFeedback(
    decisionId: string,
    accepted: boolean,
    useful: boolean | null,
  ) {
    try {
      await fetchJson(`/api/v1/decisions/${decisionId}/feedback`, {
        method: "POST",
        body: JSON.stringify({
          accepted,
          feedback_type: "dashboard",
          useful,
        }),
      });
      await refresh();
      setNotice(accepted ? "Feedback registrado: accion hecha." : "Feedback registrado.");
    } catch {
      setError("No se pudo registrar el feedback.");
    }
  }

  async function recordOperationalAction(actionType: string, tableId: string) {
    try {
      setLoading(true);
      await fetchJson("/api/v1/operational-actions", {
        method: "POST",
        body: JSON.stringify({
          action_type: actionType,
          table_id: tableId,
          target_channel: "shared_panel",
        }),
      });
      await refresh();
      setNotice("Accion operativa registrada. Estado de sala actualizado.");
    } catch {
      setError("No se pudo registrar la accion operativa.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return {
    createQueueGroup,
    decisions,
    error,
    loading,
    notice,
    queueGroups,
    refresh,
    registerFeedback,
    recordOperationalAction,
    tables,
  };
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
        <span className={`status-pill ${statusTone(analysis?.state)}`}>
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
    const analysisUrl = resolveTableServiceAnalysisUrl();
    const eventsUrl = resolveTableServiceEventsUrl();
    let eventSource: EventSource | null = null;

    async function fetchAnalysis() {
      try {
        const response = await fetch(analysisUrl);
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
    const interval = window.setInterval(() => void fetchAnalysis(), eventsUrl ? 10000 : 2000);
    if (eventsUrl && "EventSource" in window) {
      eventSource = new EventSource(eventsUrl);
      eventSource.addEventListener("table_service_analysis", (event) => {
        try {
          const payload = JSON.parse((event as MessageEvent).data) as TableServiceAnalysis;
          if (active) {
            setAnalysis(payload);
          }
        } catch {
          void fetchAnalysis();
        }
      });
      eventSource.onerror = () => {
        void fetchAnalysis();
      };
    }
    return () => {
      active = false;
      window.clearInterval(interval);
      eventSource?.close();
    };
  }, []);

  return analysis;
}

function priorityClass(priority?: string): string {
  if (priority === "P1") {
    return "priority-p1";
  }
  if (priority === "P2") {
    return "priority-p2";
  }
  return "priority-p3";
}

function modeLabel(mode: string): string {
  const labels: Record<string, string> = {
    busy: "Servicio cargado",
    critical_service: "Servicio critico",
    normal: "Operacion estable",
  };
  return labels[mode] ?? mode;
}

function modeShortLabel(mode: string): string {
  const labels: Record<string, string> = {
    busy: "Cargado",
    critical_service: "Critico",
    normal: "Normal",
  };
  return labels[mode] ?? mode;
}

function inferPressureMode(
  decisions: DecisionRecommendation[],
  queueGroups: QueueGroup[],
): string {
  if (decisions.some((decision) => decision.priority === "P1") && queueGroups.length >= 3) {
    return "critical_service";
  }
  if (decisions.length > 0 || queueGroups.length > 0) {
    return "busy";
  }
  return "normal";
}

function elapsedMinutes(value: string): number {
  const startedAt = new Date(value).getTime();
  if (Number.isNaN(startedAt)) {
    return 0;
  }
  return Math.max(0, Math.floor((Date.now() - startedAt) / 60000));
}

function formatQueueWait(value: string): string {
  const minutes = elapsedMinutes(value);
  return minutes === 0 ? "esperando ahora" : `${minutes} min esperando`;
}

function buildTableSummary(analysis: TableServiceAnalysis): string {
  if (analysis.state === "waiting_for_video") {
    return "Mesa preparada para recibir señal de cámara. Aún no hay análisis visual.";
  }
  if (analysis.people_count === 0) {
    if (analysis.state === "dirty") {
      return "No hay clientes en la mesa y quedan elementos de servicio. Prioridad de limpieza.";
    }
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
  if (analysis.service_flags.ready_for_checkout) {
    return `${analysis.people_count} cliente(s) detectados. Los platos parecen vacíos: posible momento de postre o cuenta.`;
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
        : analysis.service_flags.ready_for_checkout
          ? "Platos mayoritariamente vacíos"
        : "Sin comida detectada todavía",
      ok: true,
    },
    {
      label: "Limpieza",
      detail: analysis.service_flags.needs_cleaning
        ? "Mesa pendiente de limpieza"
        : "Sin limpieza urgente detectada",
      ok: !analysis.service_flags.needs_cleaning,
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
    dirty: "Mesa sucia",
    eating: "Comiendo",
    empty: "Vacía",
    finishing: "Finalizando",
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
    table_dirty: "Mesa sucia",
    table_finishing: "Finalizando",
    table_session_started: "Inicio de mesa",
    table_state_changed: "Cambio de estado",
  };
  return labels[eventType] ?? eventType;
}

function statusTone(state?: string): string {
  if (state === "dirty") {
    return "danger";
  }
  if (state === "finishing" || state === "away") {
    return "warning";
  }
  if (state === "eating" || state === "needs_setup" || state === "seated") {
    return "active";
  }
  return "";
}

function labelName(label: string): string {
  const labels: Record<string, string> = {
    fork: "tenedor",
    knife: "cuchillo",
    plate: "plato",
    plate_empty: "plato vacío",
    plate_full: "plato con comida",
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
