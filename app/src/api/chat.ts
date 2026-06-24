import {
  ApiError,
  createApiError,
  getApiUrl,
  jsonRequest,
} from './client';
import type { ChatRequest } from './types';

/** 接收服务端推送的一个回答文本片段。 */
export type StreamTokenHandler = (content: string) => void;

/** 使用 SSE 接收并按顺序交给调用方处理流式回答片段。 */
export async function streamQuestion(
  payload: ChatRequest,
  onToken: StreamTokenHandler,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(
      getApiUrl('/api/v1/chat/stream'),
      jsonRequest('POST', payload),
    );
  } catch {
    throw new ApiError(0, '无法连接后端服务');
  }

  if (!response.ok) {
    throw await createApiError(response);
  }
  if (!response.body) {
    throw new ApiError(response.status, '后端未返回流式内容');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    let boundary = buffer.indexOf('\n\n');
    while (boundary >= 0) {
      handleSseEvent(buffer.slice(0, boundary), onToken);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf('\n\n');
    }

    if (done) {
      break;
    }
  }

  if (buffer.trim()) {
    handleSseEvent(buffer, onToken);
  }
}

/** 解析单个 SSE 事件中的 JSON 文本片段。 */
function handleSseEvent(event: string, onToken: StreamTokenHandler): void {
  const dataLine = event.split('\n').find((line) => line.startsWith('data: '));
  if (!dataLine) {
    return;
  }

  try {
    const payload: unknown = JSON.parse(dataLine.slice(6));
    if (
      typeof payload === 'object' &&
      payload !== null &&
      'content' in payload &&
      typeof payload.content === 'string'
    ) {
      onToken(payload.content);
    }
  } catch {
    // 忽略不符合当前 SSE 协议的单个事件，继续接收后续文本片段。
  }
}