import { X } from "lucide-react";

import type { DrawerKind } from "../types";

interface ActionDrawerProps {
  open: boolean;
  kind: DrawerKind;
  onClose: () => void;
}

const drawerCopy: Record<DrawerKind, { title: string; body: string[]; action: string }> = {
  camera: {
    title: "Configuración de cámara",
    body: [
      "Define VITE_CAMERA_STREAM_URL para pintar un stream servido por el backend.",
      "También puedes probar una webcam local desde el panel de cámara.",
      "Los overlays de mesas/personas se activarán cuando lleguen observaciones reales.",
    ],
    action: "Guardar conexión",
  },
  tables: {
    title: "Detalle de mesa",
    body: [
      "Aquí se mostrarán estado, personas detectadas, sesión activa y última observación.",
      "La acción principal será marcar lista, reservar o revisar calibración.",
    ],
    action: "Abrir calibración",
  },
  people: {
    title: "Personas en sala",
    body: [
      "Vista preparada para recuento total, distribución por zona y flujo entrada/salida.",
      "No se almacena identidad ni reconocimiento facial.",
    ],
    action: "Configurar zonas",
  },
  queue: {
    title: "Cola y espera",
    body: [
      "Aquí se ajustarán umbrales de cola normal, aviso de saturación y tiempo estimado.",
      "El MVP arrancará con reglas simples y datos agregados.",
    ],
    action: "Configurar umbrales",
  },
  indicators: {
    title: "Indicadores operativos",
    body: [
      "Panel reservado para ocupación, rotación, tiempos medios y salud del pipeline.",
      "Las métricas se mantendrán accionables, sin gráficas decorativas.",
    ],
    action: "Ver métricas",
  },
  history: {
    title: "Histórico",
    body: [
      "Eventos y sesiones aparecerán aquí al conectar la API.",
      "Permitirá filtrar por mesa, rango horario y severidad.",
    ],
    action: "Exportar CSV",
  },
  settings: {
    title: "Ajustes del sistema",
    body: [
      "Configuración de sede, cámara, API local, umbrales visuales y tema.",
      "Los valores sensibles deberán quedar fuera del repositorio.",
    ],
    action: "Guardar ajustes",
  },
  alerts: {
    title: "Centro de avisos",
    body: [
      "Las alertas operativas se ordenarán por severidad y hora.",
      "Cada aviso conservará evidencia mínima y explicación breve.",
    ],
    action: "Revisar reglas",
  },
  location: {
    title: "Sede activa",
    body: [
      "La primera versión usa una sede local: La Piemontesa - Centro.",
      "Más adelante se podrá cambiar entre salones o restaurantes.",
    ],
    action: "Cambiar sede",
  },
};

export function ActionDrawer({ open, kind, onClose }: ActionDrawerProps) {
  const copy = drawerCopy[kind];

  return (
    <>
      <div className={open ? "drawer-backdrop open" : "drawer-backdrop"} onClick={onClose} />
      <aside aria-hidden={!open} className={open ? "action-drawer open" : "action-drawer"}>
        <header>
          <div>
            <span>Ventana operativa</span>
            <h2>{copy.title}</h2>
          </div>
          <button aria-label="Cerrar ventana" onClick={onClose} type="button">
            <X size={22} />
          </button>
        </header>

        <div className="drawer-body">
          {copy.body.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
          <div className="form-card">
            <label>
              Estado inicial
              <input readOnly value="Pendiente de datos reales" />
            </label>
            <label>
              Fuente
              <input readOnly value="API local / cámara pendiente" />
            </label>
          </div>
        </div>

        <footer>
          <button className="ghost-action" onClick={onClose} type="button">
            Cancelar
          </button>
          <button className="primary-action" type="button">
            {copy.action}
          </button>
        </footer>
      </aside>
    </>
  );
}
