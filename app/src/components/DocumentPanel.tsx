import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '../api/client';
import {
  deleteDocument,
  listDocuments,
  uploadDocument,
} from '../api/documents';
import type { ChunkStrategy, DocumentItem, KnowledgeBase } from '../api/types';
import { useDocumentStatusTracker } from '../hooks/useDocumentStatusTracker';
import {
  formatDateTime,
  formatFileSize,
  getDocumentStatusLabel,
} from '../utils/formatters';
import { ConfirmDialog } from './ConfirmDialog';

const ACCEPTED_EXTENSIONS = ['pdf', 'docx', 'txt', 'md'];

const CHUNK_STRATEGY_LABELS: Record<ChunkStrategy, string> = {
  recursive: '递归切分',
  sliding_window: '滑动窗口切分',
  semantic: '语义切分',
};

export type DocumentPanelProps = {
  knowledgeBase: KnowledgeBase | null;
};

/** 管理当前知识库的文档上传、导入状态和删除操作。 */
export function DocumentPanel({ knowledgeBase }: DocumentPanelProps) {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [category, setCategory] = useState('default');
  const [chunkStrategy, setChunkStrategy] = useState<ChunkStrategy>('recursive');
  const [trackedDocumentId, setTrackedDocumentId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DocumentItem | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const documentsQuery = useQuery({
    queryKey: ['documents', knowledgeBase?.id, { skip: 0, limit: 20 }],
    queryFn: () => listDocuments(knowledgeBase?.id as string, 0, 20),
    enabled: knowledgeBase !== null,
  });
  const { trackedDocument, isTracking } = useDocumentStatusTracker(
    trackedDocumentId,
    knowledgeBase?.id ?? null,
  );

  const uploadMutation = useMutation({
    mutationFn: ({
      file,
      documentCategory,
      documentChunkStrategy,
    }: {
      file: File;
      documentCategory: string;
      documentChunkStrategy: ChunkStrategy;
    }) =>
      uploadDocument(
        knowledgeBase?.id as string,
        file,
        documentCategory,
        documentChunkStrategy,
      ),
    onSuccess: (result) => {
      setSelectedFile(null);
      setTrackedDocumentId(result.document_id);
      void queryClient.invalidateQueries({ queryKey: ['documents', knowledgeBase?.id] });
    },
    onError: (error) => setErrorMessage(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      setDeleteTarget(null);
      void queryClient.invalidateQueries({ queryKey: ['documents', knowledgeBase?.id] });
    },
    onError: (error) => setErrorMessage(getErrorMessage(error)),
  });

  if (!knowledgeBase) {
    return (
      <section className="panel document-panel">
        <h2>文档</h2>
        <p className="panel-message">请选择知识库后管理文档。</p>
      </section>
    );
  }

  const handleFileChange = (file: File | null) => {
    setErrorMessage(null);
    if (file && !isSupportedDocument(file)) {
      setSelectedFile(null);
      setErrorMessage('仅支持 PDF、DOCX、TXT、Markdown 文件');
      return;
    }
    setSelectedFile(file);
  };

  return (
    <section className="panel document-panel">
      <div className="panel-heading">
        <div>
          <h2>文档</h2>
          <p>上传后将由后端异步导入到当前知识库。</p>
        </div>
      </div>

      <form
        className="upload-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!selectedFile) {
            return;
          }
          setErrorMessage(null);
          uploadMutation.mutate({
            file: selectedFile,
            documentCategory: category || 'default',
            documentChunkStrategy: chunkStrategy,
          });
        }}
      >
        <label className="file-input-label">
          选择文档
          <input
            accept=".pdf,.docx,.txt,.md"
            aria-label="选择文档"
            type="file"
            onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
          />
        </label>
        <label>
          文档分类
          <input value={category} onChange={(event) => setCategory(event.target.value)} />
        </label>
        <label>
          切分策略
          <select
            aria-label="切分策略"
            value={chunkStrategy}
            onChange={(event) => setChunkStrategy(event.target.value as ChunkStrategy)}
          >
            {Object.entries(CHUNK_STRATEGY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button className="button button-primary" disabled={!selectedFile || uploadMutation.isPending} type="submit">
          {uploadMutation.isPending ? '正在上传…' : '上传文档'}
        </button>
      </form>

      {selectedFile ? <p className="selected-file">已选择：{selectedFile.name}</p> : null}
      {errorMessage ? <p className="notice notice-error" role="alert">{errorMessage}</p> : null}
      {isTracking && trackedDocument ? (
        <p className="notice notice-progress">
          {trackedDocument.original_name}：{getDocumentStatusLabel(trackedDocument.status)}
        </p>
      ) : null}
      {trackedDocument?.status === 'failed' && trackedDocument.error_message ? (
        <p className="notice notice-error">{trackedDocument.error_message}</p>
      ) : null}

      {documentsQuery.isLoading ? <p className="panel-message">正在加载文档…</p> : null}
      {!documentsQuery.isLoading && (documentsQuery.data?.items.length ?? 0) === 0 ? (
        <p className="panel-message">当前知识库还没有文档。</p>
      ) : null}

      {(documentsQuery.data?.items ?? []).map((document) => (
        <article className="document-row" key={document.id}>
          <div>
            <h3>{document.original_name}</h3>
            <p>
              {document.category} · {CHUNK_STRATEGY_LABELS[document.chunk_strategy]} · {formatFileSize(document.file_size)} · {formatDateTime(document.updated_at)}
            </p>
            <span className={`status-tag status-${document.status}`}>
              {getDocumentStatusLabel(document.status)}
            </span>
            {document.status === 'completed' ? <span>{document.chunk_count} 个分块</span> : null}
            {document.status === 'failed' && document.error_message ? (
              <p className="document-error">{document.error_message}</p>
            ) : null}
          </div>
          <button
            aria-label={`删除 ${document.original_name}`}
            className="button button-secondary"
            type="button"
            onClick={() => setDeleteTarget(document)}
          >
            删除
          </button>
        </article>
      ))}

      <ConfirmDialog
        confirmLabel="删除文档"
        description={`将删除“${deleteTarget?.original_name ?? ''}”及其已导入内容。`}
        isOpen={deleteTarget !== null}
        isSubmitting={deleteMutation.isPending}
        title="确认删除文档"
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) {
            setErrorMessage(null);
            deleteMutation.mutate(deleteTarget.id);
          }
        }}
      />
    </section>
  );
}

/** 判断文件扩展名是否符合当前后端支持范围。 */
function isSupportedDocument(file: File): boolean {
  const extension = file.name.split('.').pop()?.toLowerCase();
  return extension !== undefined && ACCEPTED_EXTENSIONS.includes(extension);
}

/** 将接口错误转换为面向用户的文案。 */
function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return '文档正在导入，暂时不能删除';
    }
    return error.message;
  }
  return '操作失败，请稍后重试';
}
