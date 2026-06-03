"""业务服务共用异常类型。"""


class ResourceNotFoundError(Exception):
    """请求的业务资源不存在。"""


class ResourceConflictError(Exception):
    """请求与当前资源状态或业务约束冲突。"""


class ExternalStorageError(Exception):
    """MinIO 或 Milvus 外部清理失败。"""
