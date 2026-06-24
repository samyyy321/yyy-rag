import { useEffect, useState } from 'react';
import type { KnowledgeBase } from '../api/types';

export type KnowledgeBaseDialogProps = {
  mode: 'create' | 'edit';
  initialValue?: Pick<KnowledgeBase, 'name' | 'description'>;
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (value: { name: string; description: string | null }) => void;
};

/** 收集知识库名称和描述的创建、编辑表单。 */
export function KnowledgeBaseDialog({
  mode,
  initialValue,
  isOpen,
  isSubmitting,
  onClose,
  onSubmit,
}: KnowledgeBaseDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (isOpen) {
      setName(initialValue?.name ?? '');
      setDescription(initialValue?.description ?? '');
    }
  }, [initialValue, isOpen]);

  if (!isOpen) {
    return null;
  }

  const title = mode === 'create' ? '新建知识库' : '编辑知识库';

  return (
    <div className="dialog-backdrop">
      <section aria-labelledby="knowledge-base-dialog-title" className="dialog" role="dialog">
        <h2 id="knowledge-base-dialog-title">{title}</h2>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit({ name: name.trim(), description: description.trim() || null });
          }}
        >
          <label>
            名称
            <input
              autoFocus
              maxLength={100}
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            描述（可选）
            <textarea
              maxLength={2000}
              rows={4}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          <div className="dialog-actions">
            <button className="button button-secondary" disabled={isSubmitting} type="button" onClick={onClose}>
              取消
            </button>
            <button className="button button-primary" disabled={isSubmitting} type="submit">
              {isSubmitting ? '正在保存…' : '保存'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
