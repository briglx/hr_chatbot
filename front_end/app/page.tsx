// app/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChatInput } from '@/components/ChatInput'

export default function HomePage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async (content: string) => {
    setIsLoading(true)

    // Create a new conversation, then navigate into it
    const res = await fetch('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ firstMessage: content }),
    })
    const { id } = await res.json()

    router.push(`/chat/${id}`)
  }

  return (
    <div className="flex h-full flex-col">
      {/* Empty state centered in the remaining space */}
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-neutral-200 dark:border-neutral-800">
          <svg
            className="h-6 w-6 text-neutral-400"
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
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
          How can I help you today?
        </p>
        <p className="text-sm text-neutral-500">
          Start a new conversation or pick one from the sidebar.
        </p>
      </div>

      {/* ChatInput pinned to the bottom, same as on the chat route */}
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}