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

export interface NavItem {
  id: SectionId;
  label: string;
  children: string[];
}
