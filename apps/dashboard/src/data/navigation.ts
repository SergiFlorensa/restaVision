import {
  BarChart3,
  Camera,
  Clock3,
  Home,
  LayoutGrid,
  ListFilter,
  Settings,
  Users,
} from "lucide-react";

import type { SectionId } from "../types";

export const navigation = [
  {
    id: "overview",
    label: "Vista General",
    icon: Home,
    children: ["Resumen", "Cámara", "Avisos"],
  },
  {
    id: "tables",
    label: "Mapa de Mesas",
    icon: LayoutGrid,
    children: ["Salón principal", "Estados", "Zonas"],
  },
  {
    id: "cameras",
    label: "Cámaras",
    icon: Camera,
    children: ["Principal", "Stream", "Calibración"],
  },
  {
    id: "people",
    label: "Personas",
    icon: Users,
    children: ["Recuento", "Distribución", "Flujo"],
  },
  {
    id: "queue",
    label: "Cola / Espera",
    icon: ListFilter,
    children: ["Estado", "Rangos", "Recepción"],
  },
  {
    id: "indicators",
    label: "Indicadores",
    icon: BarChart3,
    children: ["KPIs", "Rangos", "Salud"],
  },
  {
    id: "history",
    label: "Histórico",
    icon: Clock3,
    children: ["Eventos", "Sesiones", "Exportar"],
  },
  {
    id: "settings",
    label: "Ajustes",
    icon: Settings,
    children: ["Restaurante", "Umbrales", "Conexiones"],
  },
] satisfies Array<{
  id: SectionId;
  label: string;
  icon: typeof Home;
  children: string[];
}>;

export function getSectionLabel(sectionId: SectionId): string {
  return navigation.find((item) => item.id === sectionId)?.label ?? "Vista General";
}
