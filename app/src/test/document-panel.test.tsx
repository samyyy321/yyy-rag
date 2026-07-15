import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import type { KnowledgeBase } from '../api/types';
import { DocumentPanel } from '../components/DocumentPanel';

const documentsApi = vi.hoisted(() => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  getDocument: vi.fn(),
  deleteDocument: vi.fn(),
}));

vi.mock('../api/documents', () => documentsApi);

const sampleKnowledgeBase: KnowledgeBase = {
  id: 'knowledge-base-1',
  name: '临床指南',
  description: null,
  created_at: '2026-09-14T00:00:00Z',
  updated_at: '2026-09-14T00:00:00Z',
};

function renderDocumentPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DocumentPanel knowledgeBase={sampleKnowledgeBase} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  documentsApi.listDocuments.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 20 });
  documentsApi.getDocument.mockResolvedValue({ id: 'document-2', status: 'pending' });
});

test('选择支持文件后显示上传操作', async () => {
  const user = userEvent.setup();
  renderDocumentPanel();

  await user.upload(
    screen.getByLabelText('选择文档'),
    new File(['正文'], '手册.md', { type: 'text/markdown' }),
  );

  expect(screen.getByText('已选择：手册.md')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '上传文档' })).toBeEnabled();
});

test('删除文档先要求确认', async () => {
  documentsApi.listDocuments.mockResolvedValue({
    items: [
      {
        id: 'document-1',
        knowledge_base_id: 'knowledge-base-1',
        original_name: '手册.md',
        object_key: 'object-key',
        content_type: 'text/markdown',
        file_size: 20,
        doc_type: 'md',
        category: 'default',
        chunk_strategy: 'recursive',
        status: 'completed',
        chunk_count: 2,
        error_message: null,
        created_at: '2026-09-14T00:00:00Z',
        updated_at: '2026-09-14T00:00:00Z',
      },
    ],
    total: 1,
    skip: 0,
    limit: 20,
  });
  renderDocumentPanel();

  await userEvent.setup().click(
    await screen.findByRole('button', { name: '删除 手册.md' }),
  );

  expect(screen.getByRole('dialog', { name: '确认删除文档' })).toBeInTheDocument();
});
test('上传时提交用户选择的切分策略', async () => {
  documentsApi.uploadDocument.mockResolvedValue({
    document_id: 'document-2',
    task_id: 'task-2',
    status: 'pending',
  });
  const user = userEvent.setup();
  renderDocumentPanel();

  await user.upload(
    screen.getByLabelText('选择文档'),
    new File(['正文'], '语义文档.md', { type: 'text/markdown' }),
  );
  await user.selectOptions(screen.getByLabelText('切分策略'), 'semantic');
  await user.click(screen.getByRole('button', { name: '上传文档' }));

  expect(documentsApi.uploadDocument).toHaveBeenCalledWith(
    'knowledge-base-1',
    expect.any(File),
    'default',
    'semantic',
  );
});
