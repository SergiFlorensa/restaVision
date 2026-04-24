import { useState } from "react";

import { ActionDrawer } from "./components/ActionDrawer";
import { HeaderBar } from "./components/HeaderBar";
import { SectionPages } from "./components/SectionPages";
import { Sidebar } from "./components/Sidebar";
import { getSectionLabel } from "./data/navigation";
import type { DrawerKind, SectionId, TableMapItem } from "./types";

export default function App() {
  const [activeSection, setActiveSection] = useState<SectionId>("overview");
  const [drawerKind, setDrawerKind] = useState<DrawerKind>("camera");
  const [drawerOpen, setDrawerOpen] = useState(false);

  function openDrawer(kind: DrawerKind) {
    setDrawerKind(kind);
    setDrawerOpen(true);
  }

  function handleTableSelect(_table: TableMapItem) {
    openDrawer("tables");
  }

  return (
    <div className="app-shell">
      <Sidebar activeSection={activeSection} onSectionChange={setActiveSection} />
      <main className="dashboard">
        <HeaderBar onOpenLocation={() => openDrawer("location")} title={getSectionLabel(activeSection)} />

        <SectionPages
          activeSection={activeSection}
          onOpenDrawer={openDrawer}
          onTableSelect={handleTableSelect}
        />
      </main>

      <ActionDrawer kind={drawerKind} onClose={() => setDrawerOpen(false)} open={drawerOpen} />
      <footer className="quote-bar">“Buon cibo, buona compagnia, buon lavoro.” 🍃</footer>
    </div>
  );
}
