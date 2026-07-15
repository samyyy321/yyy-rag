import { afterEach, expect, test, vi } from 'vitest';
import { getDocument, uploadDocument } from '../api/documents';

afterEach(() => {
  vi.unstubAllGlobals();
});

test('上传文档携带 file、category 和 chunk_strategy 表单字段', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({ document_id: 'doc-1', task_id: 'task-1', status: 'pending' }),
      { status: 202 },
    ),
  );
  vi.stubGlobal('fetch', fetchMock);

  await uploadDocument(
    'kb-1',
    new File(['内容'], '指南.md', { type: 'text/markdown' }),
    '指南',
    'semantic',
  );

  expect(fetchMock).toHaveBeenCalledWith(
    '/api/v1/knowledge-bases/kb-1/documents',
    expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
  );
  const requestOptions = fetchMock.mock.calls[0][1] as RequestInit;
  const body = requestOptions.body as FormData;
  expect(body.get('category')).toBe('指南');
  expect(body.get('chunk_strategy')).toBe('semantic');
  expect(body.get('file')).toBeInstanceOf(File);
});

test('查询文档使用文档详情路径', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ id: 'doc-1' }), { status: 200 }),
  );
  vi.stubGlobal('fetch', fetchMock);

  await getDocument('doc-1');

  expect(fetchMock).toHaveBeenCalledWith('/api/v1/documents/doc-1', undefined);
});
