import { useState } from 'react';
import { ApiError } from '../api/client';
import { streamQuestion } from '../api/chat';
import type { KnowledgeBase } from '../api/types';

export type ChatEntryPanelProps = {
  knowledgeBase: KnowledgeBase | null;
  onOpen: () => void;
};

export type ChatPageProps = {
  knowledgeBase: KnowledgeBase;
  onBack: () => void;
};

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

const DEFAULT_SETTINGS: ChatSettings = {
  role: 'patient',
  topK: 20,
  rerankTopK: 5,
  useHyde: true,
};

/** 作为工作台与独立聊天界面之间的问答入口。 */
export function ChatEntryPanel({ knowledgeBase, onOpen }: ChatEntryPanelProps) {
  return (
    <section className="panel chat-entry-panel">
      <div>
        <h2>基于此知识库提问</h2>
        <p>
          {knowledgeBase
            ? `在“${knowledgeBase.name}”中检索文档并进行流式问答。`
            : '请选择知识库后进入聊天。'}
        </p>
      </div>
      <button
        className="button button-primary"
        disabled={knowledgeBase === null}
        type="button"
        onClick={onOpen}
      >
        进入聊天
      </button>
    </section>
  );
}

/** 展示当前知识库的独立流式问答界面。 */
export function ChatPage({ knowledgeBase, onBack }: ChatPageProps) {
  const [question, setQuestion] = useState('');
  const [settings, setSettings] = useState<ChatSettings>(DEFAULT_SETTINGS);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const canSubmit = question.trim().length > 0 && !isStreaming;

  const submitQuestion = async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      return;
    }

    const answerId = `assistant-${Date.now()}`;
    setErrorMessage(null);
    setQuestion('');
    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: 'user', content: trimmedQuestion },
      { id: answerId, role: 'assistant', content: '' },
    ]);
    setIsStreaming(true);

    try {
      await streamQuestion(
        {
          knowledge_base_id: knowledgeBase.id,
          question: trimmedQuestion,
          role: settings.role,
          top_k: settings.topK,
          rerank_top_k: settings.rerankTopK,
          use_hyde: settings.useHyde,
        },
        (content) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === answerId
                ? { ...message, content: `${message.content}${content}` }
                : message,
            ),
          );
        },
      );
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <section className="chat-page">
      <header className="chat-page-header">
        <div>
          <button className="back-button" type="button" onClick={onBack}>
            返回工作台
          </button>
          <h2>知识库问答</h2>
          <p>当前知识库：{knowledgeBase.name}。每次提问会独立检索当前知识库。</p>
        </div>
      </header>

      <div aria-label="聊天记录" className="chat-messages">
        {messages.length === 0 ? (
          <p className="chat-empty">输入问题后，回答会在这里逐段显示。</p>
        ) : (
          messages.map((message) => (
            <article className={`chat-message chat-message-${message.role}`} key={message.id}>
              <strong>{message.role === 'user' ? '你' : '助手'}</strong>
              <p>{message.content || '正在生成…'}</p>
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
            placeholder="输入需要从当前知识库查询的问题"
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
            <label>
              粗检索数量
              <input
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
                type="checkbox"
                onChange={(event) =>
                  setSettings((current) => ({ ...current, useHyde: event.target.checked }))
                }
              />
              使用 HyDE 提升召回
            </label>
          </div>
        </details>

        <button className="button button-primary" disabled={!canSubmit} type="submit">
          {isStreaming ? '正在生成…' : '发送'}
        </button>
      </form>
    </section>
  );
}

/** 将接口错误转换为适合聊天界面展示的中文文案。 */
function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return '问答失败，请稍后重试';
}