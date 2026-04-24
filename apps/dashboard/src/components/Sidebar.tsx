import { ChevronDown } from "lucide-react";

import { navigation } from "../data/navigation";
import type { SectionId } from "../types";

interface SidebarProps {
  activeSection: SectionId;
  onSectionChange: (section: SectionId) => void;
}

export function Sidebar({ activeSection, onSectionChange }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div>
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            ✤
          </div>
          <div>
            <strong>RestaurIA</strong>
            <span>LA PIEMONTESA</span>
          </div>
        </div>

        <nav className="navigation" aria-label="Navegación principal">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = item.id === activeSection;
            return (
              <div className="nav-group" key={item.id}>
                <button
                  className={isActive ? "nav-item active" : "nav-item"}
                  onClick={() => onSectionChange(item.id)}
                  type="button"
                >
                  <Icon size={21} strokeWidth={1.9} />
                  <span>{item.label}</span>
                  <ChevronDown className="nav-chevron" size={16} />
                </button>

                <div className={isActive ? "submenu open" : "submenu"}>
                  {item.children.map((child) => (
                    <button key={child} onClick={() => onSectionChange(item.id)} type="button">
                      {child}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>
      </div>

      <div className="sidebar-footer">
        <div className="restaurant-seal">
          <span aria-hidden="true">⌘</span>
          <strong>LA PIEMONTESA</strong>
          <small>CUCINA ITALIANA</small>
        </div>

        <div className="profile-card">
          <div className="avatar">GR</div>
          <div>
            <strong>Giovanni R.</strong>
            <span>Encargado</span>
          </div>
          <ChevronDown size={18} />
        </div>
      </div>
    </aside>
  );
}
