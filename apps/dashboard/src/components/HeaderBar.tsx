import { CalendarDays, ChevronDown, Clock3 } from "lucide-react";

interface HeaderBarProps {
  title: string;
  onOpenLocation: () => void;
}

export function HeaderBar({ title, onOpenLocation }: HeaderBarProps) {
  return (
    <header className="topbar">
      <div className="title-block">
        <h1>{title}</h1>
        <span className="divider" />
        <p>Actualizado: esperando datos</p>
        <span className="system-status">
          <span />
          Sistema listo
        </span>
      </div>

      <div className="topbar-actions">
        <div className="soft-chip">
          <CalendarDays size={18} />
          Sin servicio activo
        </div>
        <div className="soft-chip">
          <Clock3 size={18} />
          00:00
        </div>
        <button className="location-select" onClick={onOpenLocation} type="button">
          La Piemontesa - Centro
          <ChevronDown size={18} />
        </button>
      </div>
    </header>
  );
}
