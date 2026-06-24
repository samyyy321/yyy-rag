/** 知识库接口数据。 */
export type KnowledgeBase = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

/** 知识库分页响应。 */
export type KnowledgeBaseListResponse = {
  items: KnowledgeBase[];
  total: number;
  skip: number;
  limit: number;
};

/** 文档和导入任务接口数据。 */
export type DocumentItem = {
  id: string;
  knowledge_base_id: string;
  original_name: string;
  object_key: string;
  content_type: string | null;
  file_size: number;
  doc_type: string;
  category: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  task_id?: string | null;
  task_status?: string | null;
  task_error_message?: string | null;
  task_started_at?: string | null;
  task_finished_at?: string | null;
};

/** 文档分页响应。 */
export type DocumentListResponse = {
  items: DocumentItem[];
  total: number;
  skip: number;
  limit: number;
};

/** 异步上传成功响应。 */
export type DocumentUploadResponse = {
  document_id: string;
  task_id: string;
  status: 'pending';
};

/** 问答请求参数。 */
export type ChatRequest = {
  knowledge_base_id: string;
  question: string;
  role: string;
  top_k: number;
  rerank_top_k: number;
  use_hyde: boolean;
};

/** 后端健康检查响应。 */
export type HealthResponse = {
  status: 'ok' | 'unhealthy';
};
