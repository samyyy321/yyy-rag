import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import { ChatPage } from '../components/ChatPage';

const api = vi.hoisted(() => ({
  streamQuestion: vi.fn(),
  listKnowledgeBases: vi.fn(),
}));

vi.mock('../api/chat', () => ({ streamQuestion: api.streamQuestion }));
vi.mock('../api/knowledgeBases', () => ({ listKnowledgeBases: api.listKnowledgeBases }));

function renderChatPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ChatPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.listKnowledgeBases.mockResolvedValue({
    items: [
      {
        id: 'knowledge-base-1',
        name: '临床指南',
        description: null,
        created_at: '2026-09-15T00:00:00Z',
        updated_at: '2026-09-15T00:00:00Z',
      },
    ],
    total: 1,
    skip: 0,
    limit: 100,
  });
  api.streamQuestion.mockImplementation(
    async (_payload: unknown, onToken: (token: string) => void) => {
      onToken('这是流式回答。');
    },
  );
});

test('默认文档通道需要选择知识库后才能发送', async () => {
  renderChatPage();

  expect(screen.getByRole('checkbox', { name: '文档知识库' })).toBeChecked();
  expect(await screen.findByLabelText('文档知识库选择')).toBeInTheDocument();
  await screen.findByRole('option', { name: '临床指南' });
  expect(screen.getByText('文档知识库通道需要选择知识库。')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '发送' })).toBeDisabled();
});

test('纯图谱和运营数据库请求隐藏知识库选择器且不提交知识库 ID', async () => {
  const user = userEvent.setup();
  renderChatPage();

  await user.click(screen.getByRole('checkbox', { name: '医学知识图谱' }));
  await user.click(screen.getByRole('checkbox', { name: '运营数据库' }));
  await user.click(screen.getByRole('checkbox', { name: '文档知识库' }));
  await user.type(screen.getByLabelText('问题'), '图谱和运营数据问题');
  await user.click(screen.getByRole('button', { name: '发送' }));

  expect(screen.queryByLabelText('文档知识库选择')).not.toBeInTheDocument();
  expect(api.streamQuestion).toHaveBeenCalledWith(
    expect.objectContaining({ channels: ['graph', 'sql'] }),
    expect.any(Function),
  );
  expect(api.streamQuestion.mock.calls[0][0]).not.toHaveProperty('knowledge_base_id');
  expect(await screen.findByText('这是流式回答。')).toBeInTheDocument();
});

test('文档和图谱通道发送已选知识库与两个通道', async () => {
  const user = userEvent.setup();
  renderChatPage();

  await user.click(screen.getByRole('checkbox', { name: '医学知识图谱' }));
  await user.selectOptions(await screen.findByLabelText('文档知识库选择'), 'knowledge-base-1');
  await user.type(screen.getByLabelText('问题'), '融合问题');
  await user.click(screen.getByRole('button', { name: '发送' }));

  expect(api.streamQuestion).toHaveBeenCalledWith(
    expect.objectContaining({
      knowledge_base_id: 'knowledge-base-1',
      channels: ['document', 'graph'],
      question: '融合问题',
    }),
    expect.any(Function),
  );
});
