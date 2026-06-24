import { request } from './client';
import type { HealthResponse } from './types';

/** 获取后端及其依赖服务健康状态。 */
export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/v1/health');
}
