import { Maximize2, Minimize2, MoreVertical, PlugZap, Video, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cameraMarkers } from "../data/dashboard";
import type { TableServiceAnalysis } from "../types";

interface CameraPanelProps {
  streamUrl?: string;
  onOpenSettings: () => void;
  serviceAnalysis?: TableServiceAnalysis | null;
}

export function CameraPanel({ streamUrl, onOpenSettings }: CameraPanelProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [cameraStatus, setCameraStatus] = useState("Esperando cámara");
  const [localCameraConnected, setLocalCameraConnected] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const hasStream = Boolean(streamUrl);
  const hasMarkers = cameraMarkers.length > 0;
  const showEmptyState = !hasStream && !localCameraConnected;

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setExpanded(false);
      }
    }

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  async function startLocalCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraStatus("Navegador sin acceso a cámara");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "environment" },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setLocalCameraConnected(true);
      setCameraStatus("Cámara local conectada");
    } catch {
      setLocalCameraConnected(false);
      setCameraStatus("Permiso de cámara denegado");
    }
  }

  function toggleExpanded() {
    setExpanded((current) => !current);
  }

  return (
    <section
      aria-label="Cámara principal del salón"
      className={expanded ? "panel camera-panel expanded" : "panel camera-panel"}
    >
      <div className="camera-scene">
        {hasStream ? (
          <img alt="Stream de cámara principal" className="camera-stream" src={streamUrl} />
        ) : (
          <video
            aria-label="Vista previa de cámara local"
            autoPlay
            className="camera-stream"
            muted
            playsInline
            ref={videoRef}
          />
        )}

        {showEmptyState ? (
          <div className="camera-empty-state">
            <Video size={34} />
            <strong>{cameraStatus}</strong>
            <span>Conecta una webcam local o define VITE_CAMERA_STREAM_URL para usar stream.</span>
            <div>
              <button onClick={startLocalCamera} type="button">
                <PlugZap size={17} />
                Probar cámara local
              </button>
              <button onClick={onOpenSettings} type="button">
                Configurar stream
              </button>
            </div>
          </div>
        ) : null}

        <div className="camera-topline">
          <div>
            <strong>Cámara Principal - Salón</strong>
            <span>{hasStream ? "STREAM" : "LISTA"}</span>
          </div>
          <button aria-label="Opciones de cámara" onClick={onOpenSettings} type="button">
            <MoreVertical size={22} />
          </button>
        </div>

        {hasMarkers
          ? cameraMarkers.map((marker) => (
              <div
                className="camera-marker"
                key={marker.id}
                style={{
                  height: `${marker.height}%`,
                  left: `${marker.x}%`,
                  top: `${marker.y}%`,
                  width: `${marker.width}%`,
                }}
              >
                <span>{marker.id}</span>
              </div>
            ))
          : null}

        {!showEmptyState ? (
          <div className="camera-controls">
            <button
              aria-label={expanded ? "Reducir cámara" : "Ampliar cámara"}
              onClick={toggleExpanded}
              type="button"
            >
              {expanded ? <Minimize2 size={19} /> : <Maximize2 size={19} />}
            </button>
            <button aria-label="Más opciones" onClick={onOpenSettings} type="button">
              <MoreVertical size={19} />
            </button>
            <button aria-label="Silenciar cámara" type="button">
              <VolumeX size={19} />
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
