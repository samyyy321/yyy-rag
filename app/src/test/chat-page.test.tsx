import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import type { KnowledgeBase } from '../api/types';
import { ChatEntryPanel, ChatPage } from '../components/ChatPage';

const chatApi = vi.hoisted(() => ({ streamQuestion: vi.fn() }));
vi.mock('../api/chat', () => chatApi);

const sampleKnowledgeBase: KnowledgeBase = {
  id: 'knowledge-base-1',
  name: '临床指南',
  description: null,
  created_at: '2026-09-14T00:00:00Z',
  updated_at: '2026-09-14T00:00:00Z',
};

beforeEach(() => {
  vi.clearAllMocks();
});

test('点击问答入口后通知工作台打开聊天界面', async () => {
  const onOpen = vi.fn();
  render(<ChatEntryPanel knowledgeBase={sampleKnowledgeBase} onOpen={onOpen} />);

  await userEvent.setup().click(screen.getByRole('button', { name: '进入聊天' }));

  expect(onOpen).toHaveBeenCalledOnce();
});

test('聊天界面逐段拼接流式回答且不展示来源', async () => {
  chatApi.streamQuestion.mockImplementation(
    async (_payload: unknown, onToken: (token: string) => void) => {
      onToken('这是');
      onToken('流式回答。');
    },
  );
  const user = userEvent.setup();
  render(<ChatPage knowledgeBase={sampleKnowledgeBase} onBack={vi.fn()} />);

  await user.type(screen.getByLabelText('问题'), '测试流式输出');
  await user.click(screen.getByRole('button', { name: '发送' }));

  expect(chatApi.streamQuestion).toHaveBeenCalledWith(
    expect.objectContaining({
      knowledge_base_id: 'knowledge-base-1',
      question: '测试流式输出',
      role: 'patient',
      top_k: 20,
      rerank_top_k: 5,
      use_hyde: true,
    }),
    expect.any(Function),
  );
  expect(await screen.findByText('这是流式回答。')).toBeInTheDocument();
  expect(screen.queryByText('来源')).not.toBeInTheDocument();
});