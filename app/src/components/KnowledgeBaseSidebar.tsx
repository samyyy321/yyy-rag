import type { KnowledgeBase } from '../api/types';

export type KnowledgeBaseSidebarProps = {
  items: KnowledgeBase[];
  total: number;
  selectedId: string | null;
  isLoading: boolean;
  onSelect: (knowledgeBase: KnowledgeBase) => void;
  onCreate: () => void;
};

/** 展示并切换当前操作的知识库。 */
export function KnowledgeBaseSidebar({
  items,
  total,
  selectedId,
  isLoading,
  onSelect,
  onCreate,
}: KnowledgeBaseSidebarProps) {
  return (
    <aside className="knowledge-base-sidebar" aria-label="知识库">
      <div className="sidebar-heading">
        <div>
          <h2>知识库</h2>
          <p>{total} 个知识库</p>
        </div>
        <button className="button button-primary" type="button" onClick={onCreate}>
          新建知识库
        </button>
      </div>

      {isLoading ? <p className="panel-message">正在加载知识库…</p> : null}
      {!isLoading && items.length === 0 ? (
        <p className="panel-message">创建第一个知识库后即可上传文档并开始问答。</p>
      ) : null}

      <div className="knowledge-base-list">
        {items.map((knowledgeBase) => (
          <button
            aria-label={knowledgeBase.name}
            aria-pressed={knowledgeBase.id === selectedId}
            className={`knowledge-base-item${knowledgeBase.id === selectedId ? ' is-selected' : ''}`}
            key={knowledgeBase.id}
            type="button"
            onClick={() => onSelect(knowledgeBase)}
          >
            <span>{knowledgeBase.name}</span>
            {knowledgeBase.description ? (
              <small>{knowledgeBase.description}</small>
            ) : null}
          </button>
        ))}
      </div>
    </aside>
  );
}
