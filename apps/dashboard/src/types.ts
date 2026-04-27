import type { LucideIcon } from "lucide-react";

export type TableStatus = "free" | "occupied" | "releasing" | "reserved" | "offline";

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

export interface NavItem {
  id: SectionId;
  label: string;
  children: string[];
}
