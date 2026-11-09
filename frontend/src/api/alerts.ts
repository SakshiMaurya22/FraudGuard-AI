import { apiClient } from "./client";

export interface Alert {
  id: string;
  bank_reference: string;
  pseudonymized_subject_key: string;
  risk_score: number;
  severity: string;
  status: string;
  model_version: string;
  feature_attributions: Record<string, unknown>;
  detected_at: string;
  created_at: string;
}

export async function getAlerts(): Promise<Alert[]> {
  const response = await apiClient.get<Alert[]>("/alerts");
  return response.data;
}

export async function updateAlertStatus(
  alertId: string,
  status: string
): Promise<Alert> {
  const response = await apiClient.patch<Alert>(
    `/alerts/${alertId}/status`,
    { status }
  );
  return response.data;
}