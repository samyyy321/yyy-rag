import { afterEach, describe, expect, test, vi } from 'vitest';
import { request } from '../api/client';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('request', () => {
  test('成功响应解析 JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
      ),
    );

    await expect(request<{ status: string }>('/api/v1/health')).resolves.toEqual({
      status: 'ok',
    });
  });

  test('204 响应返回 undefined', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    await expect(
      request<void>('/api/v1/documents/document-id', { method: 'DELETE' }),
    ).resolves.toBeUndefined();
  });

  test('detail 错误转换为 ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: '知识库不存在' }), { status: 404 }),
      ),
    );

    await expect(request('/api/v1/knowledge-bases/missing')).rejects.toEqual(
      expect.objectContaining({ status: 404, message: '知识库不存在' }),
    );
  });
});
