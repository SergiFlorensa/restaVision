import { Armchair, Clock3, UserRoundCheck, UsersRound } from "lucide-react";

import type { AlertItem, CameraMarker, MetricCardData, QueuePoint, TableMapItem } from "../types";

export const metrics: MetricCardData[] = [
  {
    id: "people",
    label: "Personas en Sala",
    value: "0",
    suffix: "Ahora",
    helper: "Pico hoy: 0",
    icon: UsersRound,
    tone: "green",
  },
  {
    id: "occupied",
    label: "Mesas Ocupadas",
    value: "0 / 20",
    helper: "0% ocupación",
    icon: Armchair,
    tone: "wine",
  },
  {
    id: "time",
    label: "Tiempo Promedio",
    value: "0",
    suffix: "min",
    helper: "Sin sesiones activas",
    icon: Clock3,
    tone: "green",
  },
  {
    id: "queue",
    label: "En Cola / Espera",
    value: "0",
    helper: "Tiempo est. 0 min",
    icon: UserRoundCheck,
    tone: "wine",
  },
];

export const queueSeries: QueuePoint[] = [
  { time: "11:00", groups: 0 },
  { time: "11:10", groups: 0 },
  { time: "11:20", groups: 0 },
  { time: "11:30", groups: 0 },
  { time: "11:40", groups: 0 },
  { time: "11:50", groups: 0 },
  { time: "12:00", groups: 0 },
  { time: "12:10", groups: 0 },
  { time: "12:20", groups: 0 },
  { time: "12:30", groups: 0 },
  { time: "12:40", groups: 0 },
  { time: "12:50", groups: 0 },
  { time: "13:00", groups: 0 },
];

export const tables: TableMapItem[] = [
  { id: 1, status: "free", seats: 4, x: 7, y: 19 },
  { id: 2, status: "free", seats: 4, x: 16, y: 19 },
  { id: 3, status: "free", seats: 4, x: 27, y: 19 },
  { id: 4, status: "free", seats: 4, x: 36, y: 19 },
  { id: 5, status: "free", seats: 4, x: 7, y: 47 },
  { id: 6, status: "free", seats: 4, x: 18, y: 47 },
  { id: 7, status: "free", seats: 4, x: 29, y: 47 },
  { id: 8, status: "free", seats: 4, x: 39, y: 47 },
  { id: 9, status: "free", seats: 4, x: 7, y: 78 },
  { id: 10, status: "free", seats: 4, x: 17, y: 78 },
  { id: 11, status: "free", seats: 4, x: 29, y: 78 },
  { id: 12, status: "free", seats: 4, x: 39, y: 78 },
  { id: 13, status: "free", seats: 2, x: 54, y: 55 },
  { id: 14, status: "free", seats: 2, x: 63, y: 56 },
  { id: 15, status: "free", seats: 2, x: 73, y: 56 },
  { id: 16, status: "free", seats: 2, x: 81, y: 56 },
  { id: 17, status: "free", seats: 4, x: 68, y: 25 },
  { id: 18, status: "free", seats: 4, x: 81, y: 25 },
  { id: 19, status: "free", seats: 4, x: 95, y: 28 },
  { id: 20, status: "free", seats: 4, x: 95, y: 67 },
];

export const alerts: AlertItem[] = [];

export const cameraMarkers: CameraMarker[] = [];
