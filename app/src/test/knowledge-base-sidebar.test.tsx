import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';
import { KnowledgeBaseSidebar } from '../components/KnowledgeBaseSidebar';
import type { KnowledgeBase } from '../api/types';

const sampleKnowledgeBase: KnowledgeBase = {
  id: 'knowledge-base-1',
  name: '临床指南',
  description: '用于测试的知识库',
  created_at: '2026-09-14T00:00:00Z',
  updated_at: '2026-09-14T00:00:00Z',
};

test('选择知识库并通过新建按钮触发回调', async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();
  const onCreate = vi.fn();

  render(
    <KnowledgeBaseSidebar
      items={[sampleKnowledgeBase]}
      total={1}
      selectedId={null}
      isLoading={false}
      onSelect={onSelect}
      onCreate={onCreate}
    />,
  );

  await user.click(screen.getByRole('button', { name: '临床指南' }));
  expect(onSelect).toHaveBeenCalledWith(sampleKnowledgeBase);

  await user.click(screen.getByRole('button', { name: '新建知识库' }));
  expect(onCreate).toHaveBeenCalledOnce();
});
