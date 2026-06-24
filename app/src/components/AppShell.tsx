import type { ReactNode } from 'react';

export type AppShellProps = {
  sidebar: ReactNode;
  children: ReactNode;
  healthStatus: 'checking' | 'available' | 'unavailable';
  isChatView: boolean;
  onRefreshHealth: () => void;
};

/** 提供知识库工作台和独立聊天界面的顶层页面骨架。 */
export function AppShell({
  sidebar,
  children,
  healthStatus,
  isChatView,
  onRefreshHealth,
}: AppShellProps) {
  const healthLabel = {
    checking: '检查服务',
    available: '服务可用',
    unavailable: '服务不可用',
  }[healthStatus];

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-brand">
          <p>YYY-RAG</p>
          <h1>{isChatView ? '知识库问答' : '知识库工作台'}</h1>
        </div>
        <div className={`health-status health-${healthStatus}`} role="status">
          <span>{healthLabel}</span>
          <button className="health-refresh" type="button" onClick={onRefreshHealth}>
            刷新状态
          </button>
        </div>
      </header>
      <div className={`app-content${isChatView ? ' chat-view-content' : ''}`}>
        {sidebar}
        <main className="workspace">{children}</main>
      </div>
    </div>
  );
}