/** 统一封装后端请求，集中处理响应和错误信息。 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '';

/** 根据可选的部署前缀构造后端请求地址。 */
export function getApiUrl(path: string): string {
  return `${apiBaseUrl}${path}`;
}

/** 将失败的 HTTP 响应转换为统一的前端错误。 */
export async function createApiError(response: Response): Promise<ApiError> {
  let detail: string | undefined;
  try {
    const payload: unknown = await response.json();
    if (
      typeof payload === 'object' &&
      payload !== null &&
      'detail' in payload &&
      typeof payload.detail === 'string'
    ) {
      detail = payload.detail;
    }
  } catch {
    // 非 JSON 错误响应使用状态码对应的通用提示。
  }

  if (detail) {
    return new ApiError(response.status, detail);
  }
  if (response.status === 500) {
    return new ApiError(response.status, '服务处理失败，请稍后重试');
  }
  return new ApiError(response.status, `请求失败（${response.status}）`);
}

/** 请求后端并将成功响应解析为 JSON。 */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(getApiUrl(path), init);
  } catch {
    throw new ApiError(0, '无法连接后端服务');
  }

  if (!response.ok) {
    throw await createApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** 构造 JSON 请求参数，避免各资源模块重复设置请求头。 */
export function jsonRequest(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}