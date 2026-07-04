import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import App from '../App';

const api = vi.hoisted(() => ({
  getHealth: vi.fn(),
  listKnowledgeBases: vi.fn(),
  createKnowledgeBase: vi.fn(),
  updateKnowledgeBase: vi.fn(),
  deleteKnowledgeBase: vi.fn(),
}));

vi.mock('../api/health', () => ({ getHealth: api.getHealth }));
vi.mock('../api/knowledgeBases', () => ({
  listKnowledgeBases: api.listKnowledgeBases,
  createKnowledgeBase: api.createKnowledgeBase,
  updateKnowledgeBase: api.updateKnowledgeBase,
  deleteKnowledgeBase: api.deleteKnowledgeBase,
}));

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.getHealth.mockResolvedValue({ status: 'ok' });
  api.listKnowledgeBases.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 100 });
});

test('后端健康时显示服务可用', async () => {
  renderApp();

  expect(await screen.findByText('服务可用')).toBeInTheDocument();
});

test('知识库管理页不再展示聊天入口', () => {
  renderApp();

  expect(screen.getByText('请选择知识库后管理文档。')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '进入聊天' })).not.toBeInTheDocument();
});

test('顶层导航在知识库管理和统一智能问答之间切换', async () => {
  const user = userEvent.setup();
  renderApp();

  await user.click(screen.getByRole('button', { name: '智能问答' }));

  expect(screen.getByRole('heading', { name: '统一智能问答' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '智能问答' })).toHaveAttribute(
    'aria-current',
    'page',
  );

  await user.click(screen.getByRole('button', { name: '知识库管理' }));

  expect(screen.getByText('请选择知识库后管理文档。')).toBeInTheDocument();
});
