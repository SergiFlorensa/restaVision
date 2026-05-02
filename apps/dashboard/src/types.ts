import type { LucideIcon } from "lucide-react";

export type TableStatus =
  | "free"
  | "occupied"
  | "finishing"
  | "dirty"
  | "cleaning"
  | "releasing"
  | "reserved"
  | "offline";

export type MetricTone = "green" | "wine" | "gold" | "neutral";

export type SectionId =
  | "overview"
  | "tables"
  | "cameras"
  | "people"
  | "queue"
  | "indicators"
  | "history"
  | "settings";

export type DrawerKind =
  | "camera"
  | "tables"
  | "people"
  | "queue"
  | "indicators"
  | "history"
  | "settings"
  | "alerts"
  | "location";

export interface MetricCardData {
  id: string;
  label: string;
  value: string;
  suffix?: string;
  helper: string;
  icon: LucideIcon;
  tone: MetricTone;
}

export interface TableMapItem {
  id: number;
  status: TableStatus;
  seats: number;
  x: number;
  y: number;
}

export interface AlertItem {
  id: string;
  title: string;
  description: string;
  time: string;
  tone: "critical" | "warning" | "success";
}

export interface QueuePoint {
  time: string;
  groups: number;
}

export interface CameraMarker {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ServiceAlert {
  alert_id: string;
  ts: string;
  alert_type: string;
  severity: string;
  message: string;
  evidence: Record<string, unknown>;
}

export interface ServiceTimelineEvent {
  event_id: string;
  ts: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface TableServiceAnalysis {
  table_id: string;
  updated_at: string;
  state: string;
  people_count: number;
  object_counts: Record<string, number>;
  missing_items: Record<string, number>;
  service_flags: Record<string, boolean>;
  active_alerts: ServiceAlert[];
  timeline_events: ServiceTimelineEvent[];
  seat_duration_seconds: number | null;
  away_duration_seconds: number | null;
}

export interface ApiTable {
  table_id: string;
  name: string;
  capacity: number;
  zone_id: string;
  state: string;
  people_count: number;
  people_count_peak: number;
  active_session_id: string | null;
  updated_at: string | null;
  phase: string;
  needs_attention: boolean;
  assigned_staff: string | null;
  last_attention_at: string | null;
  operational_note: string | null;
}

export interface QueueGroup {
  queue_group_id: string;
  party_size: number;
  arrival_ts: string;
  status: string;
  promised_wait_min: number | null;
  promised_wait_max: number | null;
  promised_at: string | null;
  preferred_zone_id: string | null;
}

export interface DecisionRecommendation {
  decision_id: string;
  mode: string;
  priority: "P1" | "P2" | "P3" | string;
  question: string;
  answer: string;
  table_id: string | null;
  queue_group_id: string | null;
  eta_minutes: number | null;
  confidence: number;
  impact: string;
  reason: string[];
  expires_in_seconds: number;
  metadata: Record<string, unknown>;
}

export interface NavItem {
  id: SectionId;
  label: string;
  children: string[];
}
