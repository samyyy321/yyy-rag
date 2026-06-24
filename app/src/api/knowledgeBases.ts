import { jsonRequest, request } from './client';
import type { KnowledgeBase, KnowledgeBaseListResponse } from './types';

/** 查询知识库分页列表。 */
export function listKnowledgeBases(
  skip = 0,
  limit = 100,
): Promise<KnowledgeBaseListResponse> {
  const search = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  return request<KnowledgeBaseListResponse>(`/api/v1/knowledge-bases?${search}`);
}

/** 创建知识库。 */
export function createKnowledgeBase(input: {
  name: string;
  description: string | null;
}): Promise<KnowledgeBase> {
  return request<KnowledgeBase>('/api/v1/knowledge-bases', jsonRequest('POST', input));
}

/** 更新知识库基本信息。 */
export function updateKnowledgeBase(
  knowledgeBaseId: string,
  input: { name: string; description: string | null },
): Promise<KnowledgeBase> {
  return request<KnowledgeBase>(
    `/api/v1/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}`,
    jsonRequest('PUT', input),
  );
}

/** 删除不包含文档的知识库。 */
export async function deleteKnowledgeBase(knowledgeBaseId: string): Promise<void> {
  await request<void>(
    `/api/v1/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}`,
    { method: 'DELETE' },
  );
}
