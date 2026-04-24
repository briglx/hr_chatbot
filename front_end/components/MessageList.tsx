import { Message } from '@/lib/types'
import { CodeBlock } from './CodeBlock'

interface MessageListProps {
  messages: Message[]
}

export function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-neutral-200 dark:border-neutral-700">
          <svg
            className="h-5 w-5 text-neutral-400"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            viewBox="0 0 24 24"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          How can I help you today?
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-5 py-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const parts = parseContent(message.content)

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-[11px] font-medium ${
          isUser
            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
            : 'border border-neutral-200 bg-neutral-100 text-neutral-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-400'
        }`}
      >
        {isUser ? (
          'JD'
        ) : (
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            viewBox="0 0 24 24"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        )}
      </div>

      {/* Bubble */}
      <div className={`flex max-w-[75%] flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
        <p className={`text-[11px] text-neutral-400 ${isUser ? 'text-right' : ''}`}>
          {isUser ? 'You' : 'Assistant'}
        </p>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'rounded-tr-sm bg-blue-50 text-blue-900 dark:bg-blue-950 dark:text-blue-100'
              : 'rounded-tl-sm border border-neutral-200 bg-neutral-50 text-neutral-800 dark:border-neutral-700 dark:bg-neutral-800/60 dark:text-neutral-200'
          }`}
        >
          {parts.map((part, i) =>
            part.type === 'code' ? (
              <CodeBlock key={i} language={part.language} code={part.content} />
            ) : (
              <span key={i} className="whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: renderInline(part.content) }} />
            )
          )}
        </div>
      </div>
    </div>
  )
}

// Parse message content into text,code block, and markdown segments
type Part =
  | { type: 'text'; content: string }
  | { type: 'code'; language: string; content: string }

function parseContent(content: string): Part[] {
  const parts: Part[] = []
  const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g
  let lastIndex = 0
  let match

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: content.slice(lastIndex, match.index) })
    }
    parts.push({ type: 'code', language: match[1] || 'text', content: match[2].trimEnd() })
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < content.length) {
    parts.push({ type: 'text', content: content.slice(lastIndex) })
  }

  return parts
}

// Render inline code in text
function renderInline(text: string): string {
  return text.replace(
    /`([^`]+)`/g,
    '<code class="rounded bg-neutral-200 px-1 py-0.5 font-mono text-[12px] text-neutral-800 dark:bg-neutral-700 dark:text-neutral-200">$1</code>'
  )
}
