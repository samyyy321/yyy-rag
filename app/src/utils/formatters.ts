/** 将字节大小转换为简洁可读的文本。 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** 按浏览器本地时区展示接口返回的时间。 */
export function formatDateTime(isoDateTime: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'short',
    timeStyle: 'short',
    hour12: false,
  }).format(new Date(isoDateTime));
}

/** 将后端文档状态转为面向用户的中文标签。 */
export function getDocumentStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: '等待导入',
    processing: '正在导入',
    completed: '导入完成',
    failed: '导入失败',
  };
  return labels[status] ?? status;
}
