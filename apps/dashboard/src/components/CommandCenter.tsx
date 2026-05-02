import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Headset,
  LayoutDashboard,
  ListChecks,
  RefreshCw,
  Timer,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import { apiUrl } from "../config";
import { tables } from "../data/dashboard";
import type {
  ApiTable,
  DecisionRecommendation,
  QueueGroup,
  TableMapItem,
  TableServiceAnalysis,
  TableStatus,
} from "../types";

interface CommandCenterProps {
  analysis: TableServiceAnalysis | null;
  onOpenAlerts: () => void;
  onOpenTableDetail: (table: TableMapItem) => void;
  onOpenTechnical: () => void;
}

export function CommandCenter({
  analysis,
  onOpenAlerts,
  onOpenTableDetail,
  onOpenTechnical,
}: CommandCenterProps) {
  const {
    createQueueGroup,
    decisions,
    error,
    loading,
    notice,
    queueGroups,
    refresh,
    registerFeedback,
    recordOperationalAction,
    tables: apiTables,
  } = useOperationalCopilot();
  const primary = decisions[0] ?? null;
  const waitingGroups = queueGroups.filter((group) => group.status === "waiting");
  const pressureMode = primary?.mode ?? inferPressureMode(decisions, waitingGroups);
  const readyTables = apiTables.filter((table) => table.state === "ready").length;
  const attentionTables = apiTables.filter((table) => table.needs_attention).length;
  const focusTable = primary?.table_id
    ? apiTables.find((table) => table.table_id === primary.table_id)
    : apiTables[0];

  return (
    <div className={`command-center ${priorityClass(primary?.priority)}`}>
      <div className="command-topline">
        <div>
          <span className="live-dot" />
          <strong>{modeLabel(pressureMode)}</strong>
          <small>{waitingGroups.length} grupos en cola</small>
        </div>
        <div className="command-top-actions">
          <button className="command-icon-button" onClick={refresh} title="Actualizar" type="button">
            <RefreshCw size={18} />
          </button>
          <button className="command-ghost-button" onClick={onOpenTechnical} type="button">
            <Camera size={17} />
            Tecnico
          </button>
        </div>
      </div>

      <section className="hero-command">
        <div className="hero-orbital">
          <span>{primary?.priority ?? "OK"}</span>
        </div>
        <div className="hero-command-copy">
          <span className="next-action-label">Ahora</span>
          <h2>{primary?.answer ?? "Sala bajo control"}</h2>
          <p>
            {primary
              ? formatDecisionReason(primary)
              : "Sin prioridad critica. Mantener cola y mesas en observacion."}
          </p>
        </div>
        <div className="hero-command-actions">
          <button
            className="command-primary-button"
            disabled={!primary}
            onClick={() => primary && registerFeedback(primary.decision_id, true, true)}
            type="button"
          >
            <CheckCircle2 size={18} />
            Hecho
          </button>
          <button
            className="command-secondary-button"
            disabled={!primary}
            onClick={() => primary && registerFeedback(primary.decision_id, false, null)}
            type="button"
          >
            Ignorar
          </button>
          <button
            className="command-secondary-button"
            disabled={!primary}
            onClick={() => primary && registerFeedback(primary.decision_id, false, false)}
            type="button"
          >
            No util
          </button>
        </div>
      </section>

      <section className="command-kpi-strip">
        <CommandKpi
          icon={Timer}
          label="Promesa"
          value={primary?.eta_minutes != null ? `${primary.eta_minutes}m` : "--"}
        />
        <CommandKpi icon={Users} label="Cola" value={`${waitingGroups.length}`} />
        <CommandKpi icon={CheckCircle2} label="Listas" value={`${readyTables}`} />
        <CommandKpi icon={Headset} label="Atencion" value={`${attentionTables}`} />
      </section>

      <div className="command-main-grid">
        <ServiceRoomPanel
          analysis={analysis}
          apiTables={apiTables}
          onTableSelect={onOpenTableDetail}
        />
        <div className="command-side-stack">
          <QueueConsole
            createQueueGroup={createQueueGroup}
            loading={loading}
            notice={notice}
            waitingGroups={waitingGroups}
          />
          <ActionStack decisions={decisions} loading={loading} />
        </div>
      </div>

      <div className="command-bottom-grid">
        <CrewActionDock
          focusTable={focusTable}
          loading={loading}
          recordOperationalAction={recordOperationalAction}
        />
        <VisionSignalPanel
          analysis={analysis}
          error={error}
          onOpenAlerts={onOpenAlerts}
          onOpenTechnical={onOpenTechnical}
        />
      </div>
    </div>
  );
}

function CommandKpi({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <article className="command-kpi">
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function ServiceRoomPanel({
  analysis,
  apiTables,
  onTableSelect,
}: {
  analysis: TableServiceAnalysis | null;
  apiTables: ApiTable[];
  onTableSelect: (table: TableMapItem) => void;
}) {
  const liveTables = tables.map((table) => {
    const apiTable = apiTables.find((item) => tableNumberFromId(item.table_id) === table.id);
    if (apiTable) {
      return { ...table, status: mapApiTableToStatus(apiTable) };
    }
    if (analysis && table.id === tableNumberFromId(analysis.table_id)) {
      return { ...table, status: mapAnalysisStateToTableStatus(analysis.state) };
    }
    return table;
  });

  return (
    <section className="command-panel room-command-panel">
      <div className="command-panel-header">
        <div>
          <span>Mapa tactico</span>
          <h3>Sala</h3>
        </div>
        <small>{apiTables.length || tables.length} mesas</small>
      </div>
      <div className="next-room-map" aria-label="Mapa operativo principal">
        <div className="next-room-zone kitchen">Cocina</div>
        <div className="next-room-zone bar">Barra</div>
        <div className="next-room-zone entry">Entrada</div>
        <div className="next-room-walkway" />
        {liveTables.map((table) => (
          <button
            aria-label={`Mesa ${table.id}`}
            className={`next-table-node ${table.status}`}
            key={table.id}
            onClick={() => onTableSelect(table)}
            style={{ left: `${table.x}%`, top: `${table.y}%` }}
            type="button"
          >
            <span>{table.id}</span>
            <small>{table.seats}</small>
          </button>
        ))}
      </div>
      <div className="room-legend-compact">
        <span><i className="status-dot free" />Libre</span>
        <span><i className="status-dot occupied" />Ocupada</span>
        <span><i className="status-dot finishing" />Final</span>
        <span><i className="status-dot dirty" />Limpiar</span>
      </div>
    </section>
  );
}

function QueueConsole({
  createQueueGroup,
  loading,
  notice,
  waitingGroups,
}: {
  createQueueGroup: (partySize: number) => Promise<void>;
  loading: boolean;
  notice: string | null;
  waitingGroups: QueueGroup[];
}) {
  return (
    <section className="command-panel queue-console">
      <div className="command-panel-header">
        <div>
          <span>Entrada</span>
          <h3>Cola</h3>
        </div>
        <strong>{waitingGroups.length}</strong>
      </div>
      <div className="quick-party-actions next">
        {[2, 4, 6].map((partySize) => (
          <button
            disabled={loading}
            key={partySize}
            onClick={() => createQueueGroup(partySize)}
            type="button"
          >
            +{partySize}
          </button>
        ))}
      </div>
      {notice ? <p className="operation-notice next">{notice}</p> : null}
      <div className="queue-pulse-list">
        {waitingGroups.slice(0, 5).map((group) => (
          <article key={group.queue_group_id}>
            <strong>G{group.party_size}</strong>
            <span>{formatQueueWait(group.arrival_ts)}</span>
          </article>
        ))}
        {waitingGroups.length === 0 ? <span className="muted-line">Sin espera activa</span> : null}
      </div>
    </section>
  );
}

function ActionStack({
  decisions,
  loading,
}: {
  decisions: DecisionRecommendation[];
  loading: boolean;
}) {
  return (
    <section className="command-panel action-stack-panel">
      <div className="command-panel-header">
        <div>
          <span>Siguiente</span>
          <h3>Top 3</h3>
        </div>
        <ListChecks size={20} />
      </div>
      <div className="next-action-stack">
        {decisions.length > 0 ? (
          decisions.slice(0, 3).map((decision, index) => (
            <article key={decision.decision_id}>
              <b>{index + 1}</b>
              <div>
                <strong>{decision.answer}</strong>
                <small>{formatDecisionReason(decision)}</small>
              </div>
              <span className={priorityClass(decision.priority)}>{decision.priority}</span>
            </article>
          ))
        ) : (
          <article className="empty-next-action">
            <b>0</b>
            <div>
              <strong>Sin accion pendiente</strong>
              <small>{loading ? "Calculando..." : "Crea cola o cambia estados."}</small>
            </div>
          </article>
        )}
      </div>
    </section>
  );
}

function CrewActionDock({
  focusTable,
  loading,
  recordOperationalAction,
}: {
  focusTable: ApiTable | undefined;
  loading: boolean;
  recordOperationalAction: (actionType: string, tableId: string) => Promise<void>;
}) {
  return (
    <section className="command-panel crew-dock">
      <div className="command-panel-header">
        <div>
          <span>Equipo</span>
          <h3>{focusTable?.name ?? "Sin mesa foco"}</h3>
        </div>
        <Headset size={20} />
      </div>
      <div className="crew-action-grid">
        <button
          disabled={loading || !focusTable}
          onClick={() => focusTable && recordOperationalAction("mark_needs_attention", focusTable.table_id)}
          type="button"
        >
          Revisar
        </button>
        <button
          disabled={loading || !focusTable}
          onClick={() => focusTable && recordOperationalAction("request_bill", focusTable.table_id)}
          type="button"
        >
          Cuenta
        </button>
        <button
          disabled={loading || !focusTable}
          onClick={() => focusTable && recordOperationalAction("start_cleaning", focusTable.table_id)}
          type="button"
        >
          Limpiar
        </button>
        <button
          disabled={loading || !focusTable}
          onClick={() => focusTable && recordOperationalAction("cleaning_done", focusTable.table_id)}
          type="button"
        >
          Lista
        </button>
      </div>
    </section>
  );
}

function VisionSignalPanel({
  analysis,
  error,
  onOpenAlerts,
  onOpenTechnical,
}: {
  analysis: TableServiceAnalysis | null;
  error: string | null;
  onOpenAlerts: () => void;
  onOpenTechnical: () => void;
}) {
  return (
    <section className="command-panel vision-signal-panel">
      <div className="command-panel-header">
        <div>
          <span>Vision</span>
          <h3>{analysis ? stateLabel(analysis.state) : "Sin video"}</h3>
        </div>
        <LayoutDashboard size={20} />
      </div>
      {error ? (
        <p className="operation-error next"><AlertTriangle size={16} />{error}</p>
      ) : (
        <p>{analysis ? buildTableSummary(analysis) : "La vision queda en segundo plano hasta recibir senal estable."}</p>
      )}
      <div className="vision-actions">
        <button onClick={onOpenTechnical} type="button">Camara</button>
        <button onClick={onOpenAlerts} type="button">Registro</button>
      </div>
    </section>
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
      setNotice(`Grupo de ${partySize} anadido. Recomendacion recalculada.`);
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
  return minutes === 0 ? "ahora" : `${minutes} min`;
}

function formatDecisionReason(decision: DecisionRecommendation): string {
  return decision.reason.join(" / ") || decision.impact;
}

function tableNumberFromId(tableId: string): number | null {
  const match = tableId.match(/(\d+)$/);
  return match ? Number(match[1]) : null;
}

function mapApiTableToStatus(table: ApiTable): TableStatus {
  if (table.needs_attention) {
    return "dirty";
  }
  if (table.state === "ready") {
    return "free";
  }
  if (table.state === "payment" || table.phase === "bill_requested") {
    return "finishing";
  }
  if (table.state === "pending_cleaning") {
    return "dirty";
  }
  return "occupied";
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

function stateLabel(state: string): string {
  const labels: Record<string, string> = {
    away: "Cliente ausente",
    dirty: "Mesa sucia",
    eating: "Comiendo",
    empty: "Vacia",
    finishing: "Finalizando",
    needs_setup: "Falta servicio",
    observing: "Observando",
    seated: "Sentado",
    waiting_for_video: "Sin video",
  };
  return labels[state] ?? state;
}

function buildTableSummary(analysis: TableServiceAnalysis): string {
  if (analysis.state === "waiting_for_video") {
    return "Esperando senal estable de camara. El panel operativo sigue funcionando con datos manuales.";
  }
  if (analysis.people_count === 0) {
    if (analysis.state === "dirty") {
      return "Mesa vacia con servicio pendiente: posible limpieza prioritaria.";
    }
    return "Sin clientes detectados en la mesa enfocada.";
  }
  if (analysis.service_flags.ready_for_checkout) {
    return "Mesa en posible fase final: puede convertirse en oportunidad para la cola.";
  }
  return `${analysis.people_count} cliente(s) detectados. Sin incidencia critica visual.`;
}
