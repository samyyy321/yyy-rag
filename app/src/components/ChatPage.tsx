import { type ReactNode, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../api/client';
import { streamQuestion } from '../api/chat';
import { listKnowledgeBases } from '../api/knowledgeBases';
import type { ChatRequest, RetrievalChannel } from '../api/types';

type ChatSettings = {
  role: 'patient' | 'doctor' | 'pharmacist';
  topK: number;
  rerankTopK: number;
  useHyde: boolean;
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

const CHANNEL_OPTIONS: Array<{
  value: RetrievalChannel;
  label: string;
  description: string;
}> = [
  { value: 'document', label: '文档知识库', description: '检索已上传文档' },
  { value: 'graph', label: '医学知识图谱', description: '查询 Neo4j 演示图谱' },
  { value: 'sql', label: '运营数据库', description: '查询运营演示数据' },
];

const DEFAULT_SETTINGS: ChatSettings = {
  role: 'patient',
  topK: 20,
  rerankTopK: 5,
  useHyde: true,
};

/** 提供 document、graph、sql 单通道或融合检索的唯一流式聊天界面。 */
export function ChatPage() {
  const [question, setQuestion] = useState('');
  const [channels, setChannels] = useState<RetrievalChannel[]>(['document']);
  const [knowledgeBaseId, setKnowledgeBaseId] = useState('');
  const [settings, setSettings] = useState<ChatSettings>(DEFAULT_SETTINGS);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const documentSelected = channels.includes('document');
  const knowledgeBasesQuery = useQuery({
    queryKey: ['knowledge-bases', { skip: 0, limit: 100 }],
    queryFn: () => listKnowledgeBases(0, 100),
    enabled: documentSelected,
  });
  const knowledgeBases = knowledgeBasesQuery.data?.items ?? [];
  const requiresKnowledgeBase = documentSelected && !knowledgeBaseId;
  const canSubmit =
    question.trim().length > 0 &&
    channels.length > 0 &&
    !requiresKnowledgeBase &&
    !isStreaming;

  const toggleChannel = (channel: RetrievalChannel) => {
    const nextChannels = channels.includes(channel)
      ? channels.filter((item) => item !== channel)
      : [...channels, channel];
    setChannels(nextChannels);
    if (!nextChannels.includes('document')) {
      setKnowledgeBaseId('');
    }
  };

  const submitQuestion = async () => {
    const trimmedQuestion = question.trim();
    if (!canSubmit || !trimmedQuestion) {
      return;
    }

    const answerId = `assistant-${Date.now()}`;
    const payload: ChatRequest = {
      channels,
      question: trimmedQuestion,
      role: settings.role,
      top_k: settings.topK,
      rerank_top_k: settings.rerankTopK,
      use_hyde: settings.useHyde,
    };
    if (documentSelected && knowledgeBaseId) {
      payload.knowledge_base_id = knowledgeBaseId;
    }

    setErrorMessage(null);
    setQuestion('');
    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: 'user', content: trimmedQuestion },
      { id: answerId, role: 'assistant', content: '' },
    ]);
    setIsStreaming(true);

    try {
      await streamQuestion(payload, (content) => {
        setMessages((current) =>
          current.map((message) =>
            message.id === answerId
              ? { ...message, content: `${message.content}${content}` }
              : message,
          ),
        );
      });
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <section className="chat-page">
      <header className="chat-page-header">
        <h2>统一智能问答</h2>
        <p>选择一个或多个检索通道，多个通道会由后端并行检索并融合回答。</p>
      </header>

      <fieldset className="channel-selector" disabled={isStreaming}>
        <legend>检索通道</legend>
        <div className="channel-options">
          {CHANNEL_OPTIONS.map((channel) => (
            <label className="channel-option" key={channel.value}>
              <input
                aria-label={channel.label}
                checked={channels.includes(channel.value)}
                type="checkbox"
                onChange={() => toggleChannel(channel.value)}
              />
              <span>
                <strong>{channel.label}</strong>
                <small>{channel.description}</small>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {channels.length === 0 ? (
        <p className="notice notice-error" role="alert">至少选择一个检索通道。</p>
      ) : null}

      {documentSelected ? (
        <section className="knowledge-base-selector">
          <label>
            文档知识库
            <select
              aria-label="文档知识库选择"
              disabled={isStreaming || knowledgeBasesQuery.isLoading || knowledgeBases.length === 0}
              value={knowledgeBaseId}
              onChange={(event) => setKnowledgeBaseId(event.target.value)}
            >
              <option value="">请选择知识库</option>
              {knowledgeBases.map((knowledgeBase) => (
                <option key={knowledgeBase.id} value={knowledgeBase.id}>
                  {knowledgeBase.name}
                </option>
              ))}
            </select>
          </label>
          {knowledgeBasesQuery.isLoading ? <p>正在加载知识库。</p> : null}
          {!knowledgeBasesQuery.isLoading && knowledgeBases.length === 0 ? (
            <p>暂无知识库，请先在知识库管理中创建。</p>
          ) : null}
          {requiresKnowledgeBase && knowledgeBases.length > 0 ? (
            <p>文档知识库通道需要选择知识库。</p>
          ) : null}
        </section>
      ) : null}
      <div aria-label="聊天记录" className="chat-messages">
        {messages.length === 0 ? (
          <p className="chat-empty">输入问题后，回答会在这里逐段显示。</p>
        ) : (
          messages.map((message) => (
            <article className={`chat-message chat-message-${message.role}`} key={message.id}>
              <strong>{message.role === 'user' ? '你' : '助手'}</strong>
              <p>{renderInlineMarkdown(message.content || '正在生成…')}</p>
            </article>
          ))
        )}
      </div>

      {errorMessage ? <p className="notice notice-error" role="alert">{errorMessage}</p> : null}

      <form
        className="chat-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void submitQuestion();
        }}
      >
        <label>
          问题
          <textarea
            disabled={isStreaming}
            placeholder="输入需要查询的问题"
            rows={3}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
        </label>

        <details className="chat-settings">
          <summary>高级检索设置</summary>
          <div className="settings-grid">
            <label>
              回答角色
              <select
                disabled={isStreaming}
                value={settings.role}
                onChange={(event) =>
                  setSettings((current) => ({
                    ...current,
                    role: event.target.value as ChatSettings['role'],
                  }))
                }
              >
                <option value="patient">普通用户</option>
                <option value="doctor">医生</option>
                <option value="pharmacist">药师</option>
              </select>
            </label>
            {documentSelected ? (
              <>
                <label>
                  粗检索数量
                  <input
                    disabled={isStreaming}
                    min="1"
                    type="number"
                    value={settings.topK}
                    onChange={(event) => {
                      const topK = Number(event.target.value) || 1;
                      setSettings((current) => ({
                        ...current,
                        topK,
                        rerankTopK: Math.min(current.rerankTopK, topK),
                      }));
                    }}
                  />
                </label>
                <label>
                  重排数量
                  <input
                    disabled={isStreaming}
                    max={settings.topK}
                    min="1"
                    type="number"
                    value={settings.rerankTopK}
                    onChange={(event) =>
                      setSettings((current) => ({
                        ...current,
                        rerankTopK: Math.min(Number(event.target.value) || 1, current.topK),
                      }))
                    }
                  />
                </label>
                <label className="checkbox-label">
                  <input
                    checked={settings.useHyde}
                    disabled={isStreaming}
                    type="checkbox"
                    onChange={(event) =>
                      setSettings((current) => ({ ...current, useHyde: event.target.checked }))
                    }
                  />
                  使用 HyDE 提升召回
                </label>
              </>
            ) : null}
          </div>
        </details>

        <button className="button button-primary" disabled={!canSubmit} type="submit">
          {isStreaming ? '正在生成…' : '发送'}
        </button>
      </form>
    </section>
  );
}


/** 仅解析回答中的 Markdown 加粗标记，避免将模型文本作为 HTML 注入页面。 */
function renderInlineMarkdown(content: string): ReactNode[] {
  return content
    .split(/(\*\*[^*]+\*\*)/g)
    .filter((part) => part.length > 0)
    .map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
}/** 将接口错误转换为适合统一聊天界面展示的中文文案。 */
function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return '问答失败，请稍后重试';
}