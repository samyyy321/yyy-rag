export type ConfirmDialogProps = {
  title: string;
  description: string;
  confirmLabel: string;
  isOpen: boolean;
  isSubmitting?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

/** 通用的不可逆操作二次确认弹窗。 */
export function ConfirmDialog({
  title,
  description,
  confirmLabel,
  isOpen,
  isSubmitting = false,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="dialog-backdrop">
      <section aria-labelledby="confirm-dialog-title" className="dialog" role="dialog">
        <h2 id="confirm-dialog-title">{title}</h2>
        <p>{description}</p>
        <div className="dialog-actions">
          <button className="button button-secondary" disabled={isSubmitting} type="button" onClick={onCancel}>
            取消
          </button>
          <button className="button button-danger" disabled={isSubmitting} type="button" onClick={onConfirm}>
            {isSubmitting ? '正在删除…' : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
