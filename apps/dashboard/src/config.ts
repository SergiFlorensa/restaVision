export const dashboardConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000",
  cameraStreamUrl: import.meta.env.VITE_CAMERA_STREAM_URL ?? "",
  tableServiceAnalysisUrl: import.meta.env.VITE_TABLE_SERVICE_ANALYSIS_URL ?? "",
  tableServiceEventsUrl: import.meta.env.VITE_TABLE_SERVICE_EVENTS_URL ?? "",
};

export function resolveCameraStreamUrl(): string {
  if (dashboardConfig.cameraStreamUrl) {
    return dashboardConfig.cameraStreamUrl;
  }
  return `${dashboardConfig.apiBaseUrl}/api/v1/demo/table-service/stream?source=0&table_id=table_01&image_size=320&inference_stride=3&text_overlay=false`;
}

export function resolveTableServiceAnalysisUrl(): string {
  if (dashboardConfig.tableServiceAnalysisUrl) {
    return dashboardConfig.tableServiceAnalysisUrl;
  }
  return `${dashboardConfig.apiBaseUrl}/api/v1/demo/table-service/analysis?table_id=table_01`;
}

export function resolveTableServiceEventsUrl(): string {
  if (dashboardConfig.tableServiceEventsUrl) {
    return dashboardConfig.tableServiceEventsUrl;
  }
  return `${dashboardConfig.apiBaseUrl}/api/v1/demo/table-service/events/stream?table_id=table_01`;
}

export function apiUrl(path: string): string {
  return `${dashboardConfig.apiBaseUrl}${path}`;
}
