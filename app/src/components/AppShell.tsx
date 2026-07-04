import type { ReactNode } from 'react';

export type AppView = 'workspace' | 'chat';

export type AppShellProps = {
  sidebar: ReactNode;
  children: ReactNode;
  activeView: AppView;
  healthStatus: 'checking' | 'available' | 'unavailable';
  onRefreshHealth: () => void;
  onViewChange: (view: AppView) => void;
};

/** 提供知识库管理和统一智能问答的顶层页面骨架。 */
export function AppShell({
  sidebar,
  children,
  activeView,
  healthStatus,
  onRefreshHealth,
  onViewChange,
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
          <h1>知识库工作台</h1>
        </div>
        <nav aria-label="主导航" className="app-navigation">
          <button
            aria-current={activeView === 'workspace' ? 'page' : undefined}
            className={`app-navigation-item${activeView === 'workspace' ? ' is-active' : ''}`}
            type="button"
            onClick={() => onViewChange('workspace')}
          >
            知识库管理
          </button>
          <button
            aria-current={activeView === 'chat' ? 'page' : undefined}
            className={`app-navigation-item${activeView === 'chat' ? ' is-active' : ''}`}
            type="button"
            onClick={() => onViewChange('chat')}
          >
            智能问答
          </button>
        </nav>
        <div className={`health-status health-${healthStatus}`} role="status">
          <span>{healthLabel}</span>
          <button className="health-refresh" type="button" onClick={onRefreshHealth}>
            刷新状态
          </button>
        </div>
      </header>
      <div className={`app-content${activeView === 'chat' ? ' chat-view-content' : ''}`}>
        {sidebar}
        <main className="workspace">{children}</main>
      </div>
    </div>
  );
}