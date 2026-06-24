import { request } from './client';
import type {
  DocumentItem,
  DocumentListResponse,
  DocumentUploadResponse,
} from './types';

/** 查询指定知识库的文档分页列表。 */
export function listDocuments(
  knowledgeBaseId: string,
  skip = 0,
  limit = 20,
): Promise<DocumentListResponse> {
  const search = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  return request<DocumentListResponse>(
    `/api/v1/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents?${search}`,
  );
}

/** 上传一个原始文档并创建异步导入任务。 */
export function uploadDocument(
  knowledgeBaseId: string,
  file: File,
  category: string,
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', category);

  return request<DocumentUploadResponse>(
    `/api/v1/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents`,
    { method: 'POST', body: formData },
  );
}

/** 查询文档和最新导入任务状态。 */
export function getDocument(documentId: string): Promise<DocumentItem> {
  return request<DocumentItem>(`/api/v1/documents/${encodeURIComponent(documentId)}`);
}

/** 删除完成或失败的文档。 */
export async function deleteDocument(documentId: string): Promise<void> {
  await request<void>(`/api/v1/documents/${encodeURIComponent(documentId)}`, {
    method: 'DELETE',
  });
}
