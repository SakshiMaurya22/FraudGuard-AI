import { apiClient } from "./client";

export interface LivenessResponse { status: string }
export interface ReadinessResponse { status: string; database: string }

export const fetchLiveness = async () =>
  (await apiClient.get<LivenessResponse>("/health")).data;

export const fetchReadiness = async () =>
  (await apiClient.get<ReadinessResponse>("/health/ready")).data;
