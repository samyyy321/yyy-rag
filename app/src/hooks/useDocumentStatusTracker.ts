import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getDocument } from '../api/documents';
import type { DocumentItem } from '../api/types';

const ACTIVE_STATUSES = new Set(['pending', 'processing']);

/** 轮询刚上传文档的详情，进入终态后停止并刷新所属文档列表。 */
export function useDocumentStatusTracker(
  documentId: string | null,
  knowledgeBaseId: string | null,
): { trackedDocument: DocumentItem | null; isTracking: boolean } {
  const queryClient = useQueryClient();
  const documentQuery = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => getDocument(documentId as string),
    enabled: documentId !== null,
    refetchInterval: (query) =>
      isActiveIngestion(query.state.data?.status) ? 2000 : false,
  });

  useEffect(() => {
    if (
      knowledgeBaseId &&
      documentQuery.data &&
      !isActiveIngestion(documentQuery.data.status)
    ) {
      void queryClient.invalidateQueries({
        queryKey: ['documents', knowledgeBaseId],
      });
    }
  }, [documentQuery.data, knowledgeBaseId, queryClient]);

  return {
    trackedDocument: documentQuery.data ?? null,
    isTracking: isActiveIngestion(documentQuery.data?.status),
  };
}

/** 判断导入任务是否仍需轮询。 */
function isActiveIngestion(status: string | undefined): boolean {
  return status !== undefined && ACTIVE_STATUSES.has(status);
}
