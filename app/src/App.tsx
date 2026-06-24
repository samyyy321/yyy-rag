import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from './api/client';
import { getHealth } from './api/health';
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  listKnowledgeBases,
  updateKnowledgeBase,
} from './api/knowledgeBases';
import type { KnowledgeBase } from './api/types';
import { AppShell } from './components/AppShell';
import { ChatEntryPanel, ChatPage } from './components/ChatPage';
import { ConfirmDialog } from './components/ConfirmDialog';
import { DocumentPanel } from './components/DocumentPanel';
import { KnowledgeBaseDialog } from './components/KnowledgeBaseDialog';
import { KnowledgeBaseSidebar } from './components/KnowledgeBaseSidebar';
import './styles/global.css';

type DialogMode = 'create' | 'edit' | null;

/** 管理知识库工作台、当前知识库和独立聊天界面切换。 */
export default function App() {
  const queryClient = useQueryClient();
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState<string | null>(null);
  const [dialogMode, setDialogMode] = useState<DialogMode>(null);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const knowledgeBasesQuery = useQuery({
    queryKey: ['knowledge-bases', { skip: 0, limit: 100 }],
    queryFn: () => listKnowledgeBases(0, 100),
  });
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    retry: false,
  });

  const knowledgeBases = knowledgeBasesQuery.data?.items ?? [];
  const selectedKnowledgeBase = useMemo(
    () => knowledgeBases.find((item) => item.id === selectedKnowledgeBaseId) ?? null,
    [knowledgeBases, selectedKnowledgeBaseId],
  );
  const healthStatus = healthQuery.isPending
    ? 'checking'
    : healthQuery.data?.status === 'ok'
      ? 'available'
      : 'unavailable';

  const refreshKnowledgeBases = () =>
    queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });

  const createMutation = useMutation({
    mutationFn: createKnowledgeBase,
    onSuccess: (created) => {
      setSelectedKnowledgeBaseId(created.id);
      setDialogMode(null);
      void refreshKnowledgeBases();
    },
    onError: (error) => setErrorMessage(getErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, value }: { id: string; value: { name: string; description: string | null } }) =>
      updateKnowledgeBase(id, value),
    onSuccess: () => {
      setDialogMode(null);
      void refreshKnowledgeBases();
    },
    onError: (error) => setErrorMessage(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteKnowledgeBase,
    onSuccess: (_, deletedId) => {
      if (selectedKnowledgeBaseId === deletedId) {
        setSelectedKnowledgeBaseId(null);
        setIsChatOpen(false);
      }
      setIsDeleteOpen(false);
      void refreshKnowledgeBases();
    },
    onError: (error) => setErrorMessage(getErrorMessage(error)),
  });

  const submitKnowledgeBase = (value: { name: string; description: string | null }) => {
    setErrorMessage(null);
    if (dialogMode === 'edit' && selectedKnowledgeBase) {
      updateMutation.mutate({ id: selectedKnowledgeBase.id, value });
      return;
    }
    createMutation.mutate(value);
  };

  const sidebar = isChatOpen ? null : (
    <KnowledgeBaseSidebar
      isLoading={knowledgeBasesQuery.isLoading}
      items={knowledgeBases}
      selectedId={selectedKnowledgeBaseId}
      total={knowledgeBasesQuery.data?.total ?? 0}
      onCreate={() => {
        setErrorMessage(null);
        setDialogMode('create');
      }}
      onSelect={(knowledgeBase) => {
        setErrorMessage(null);
        setIsChatOpen(false);
        setSelectedKnowledgeBaseId(knowledgeBase.id);
      }}
    />
  );

  return (
    <AppShell
      healthStatus={healthStatus}
      isChatView={isChatOpen}
      sidebar={sidebar}
      onRefreshHealth={() => {
        void healthQuery.refetch();
      }}
    >
      {isChatOpen && selectedKnowledgeBase ? (
        <ChatPage knowledgeBase={selectedKnowledgeBase} onBack={() => setIsChatOpen(false)} />
      ) : (
        <>
          {errorMessage ? (
            <div className="notice notice-error" role="alert">
              {errorMessage}
            </div>
          ) : null}

          {selectedKnowledgeBase ? (
            <section className="workspace-summary">
              <div>
                <p className="section-kicker">当前知识库</p>
                <h2>{selectedKnowledgeBase.name}</h2>
                <p>{selectedKnowledgeBase.description || '未填写知识库描述。'}</p>
              </div>
              <div className="summary-actions">
                <button className="button button-secondary" type="button" onClick={() => setDialogMode('edit')}>
                  编辑
                </button>
                <button className="button button-danger" type="button" onClick={() => setIsDeleteOpen(true)}>
                  删除知识库
                </button>
              </div>
            </section>
          ) : (
            <section className="empty-workspace">
              <h2>从知识库开始</h2>
              <p>选择左侧知识库，或创建一个知识库后上传文档并开始问答。</p>
              <button className="button button-primary" type="button" onClick={() => setDialogMode('create')}>
                新建知识库
              </button>
            </section>
          )}

          <div className="workspace-panels">
            <DocumentPanel knowledgeBase={selectedKnowledgeBase} />
            <ChatEntryPanel
              knowledgeBase={selectedKnowledgeBase}
              onOpen={() => setIsChatOpen(true)}
            />
          </div>
        </>
      )}

      <KnowledgeBaseDialog
        initialValue={selectedKnowledgeBase ?? undefined}
        isOpen={dialogMode !== null}
        isSubmitting={createMutation.isPending || updateMutation.isPending}
        mode={dialogMode === 'edit' ? 'edit' : 'create'}
        onClose={() => setDialogMode(null)}
        onSubmit={submitKnowledgeBase}
      />
      <ConfirmDialog
        confirmLabel="删除知识库"
        description="删除后无法恢复。知识库中仍有文档时，后端会拒绝此操作。"
        isOpen={isDeleteOpen}
        isSubmitting={deleteMutation.isPending}
        title="确认删除知识库"
        onCancel={() => setIsDeleteOpen(false)}
        onConfirm={() => {
          if (selectedKnowledgeBase) {
            setErrorMessage(null);
            deleteMutation.mutate(selectedKnowledgeBase.id);
          }
        }}
      />
    </AppShell>
  );
}

/** 将接口错误转换为适合工作台展示的中文文案。 */
function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return '操作失败，请稍后重试';
}