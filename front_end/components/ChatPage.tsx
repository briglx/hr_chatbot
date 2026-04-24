'use client'

import { useState } from 'react'
import { Message, Conversation } from '@/lib/types'
import { MessageList } from '@/components/MessageList'
import { ChatInput } from '@/components/ChatInput'
import { ShareIcon, EllipsisVerticalIcon } from '@heroicons/react/24/outline'

interface ChatPageProps {
  conversation: Conversation
  onUpdateConversation?: (updated: Conversation) => void
}

export function ChatPage({ conversation, onUpdateConversation }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>(conversation.messages)
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async (content: string) => {
    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content,
      createdAt: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      // Replace with your actual API call
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversationId: conversation.id,
          messages: [...messages, userMessage].map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      })

      if (!response.ok) throw new Error('Failed to send message')

      const data = await response.json()

      const assistantMessage: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: data.content,
        createdAt: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
      onUpdateConversation?.({
        ...conversation,
        messages: [...messages, userMessage, assistantMessage],
        updatedAt: new Date(),
      })
    } catch (error) {
      console.error('Chat error:', error)
      // Optionally show an error toast here
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-neutral-200 px-5 py-3.5 dark:border-neutral-800">
        <h1 className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">
          {conversation.title}
        </h1>
        <div className="flex gap-1.5">
          <IconButton icon={<ShareIcon className="h-4 w-4" />} label="Share" />
          <IconButton icon={<EllipsisVerticalIcon className="h-4 w-4" />} label="More options" />
        </div>
      </header>

      {/* Messages */}
      <MessageList messages={messages} />

      {/* Input */}
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}

function IconButton({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button
      aria-label={label}
      className="flex h-8 w-8 items-center justify-center rounded-lg border border-neutral-200 text-neutral-500 transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800"
    >
      {icon}
    </button>
  )
}
