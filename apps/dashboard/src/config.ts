export const dashboardConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000",
  cameraStreamUrl: import.meta.env.VITE_CAMERA_STREAM_URL ?? "",
};

export function resolveCameraStreamUrl(): string {
  if (dashboardConfig.cameraStreamUrl) {
    return dashboardConfig.cameraStreamUrl;
  }
  return `${dashboardConfig.apiBaseUrl}/api/v1/demo/yolo-restaurant/stream?source=0&image_size=320&inference_stride=3`;
}
