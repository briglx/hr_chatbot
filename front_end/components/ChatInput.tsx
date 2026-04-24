'use client'

import { useState, useRef, KeyboardEvent, ChangeEvent } from 'react'
import { PaperClipIcon, PhotoIcon, ArrowUpIcon } from '@heroicons/react/24/outline'

interface ChatInputProps {
  onSend: (content: string) => void
  isLoading?: boolean
  disabled?: boolean
}

export function ChatInput({ onSend, isLoading = false, disabled = false }: ChatInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value)
    // Auto-resize
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`
    }
  }

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || isLoading || disabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const canSend = value.trim().length > 0 && !isLoading && !disabled

  return (
    <div className="px-5 pb-5 pt-3">
      <div className="overflow-hidden rounded-xl border border-neutral-200 bg-neutral-50 transition-colors focus-within:border-neutral-400 dark:border-neutral-700 dark:bg-neutral-800/60 dark:focus-within:border-neutral-500">
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask a follow-up..."
          rows={1}
          disabled={disabled}
          className="w-full resize-none bg-transparent px-4 pt-3 pb-2 text-sm text-neutral-900 placeholder-neutral-400 outline-none dark:text-neutral-100 dark:placeholder-neutral-500"
          style={{ maxHeight: '200px' }}
        />

        {/* Footer bar */}
        <div className="flex items-center justify-between px-3 pb-2.5">
          <div className="flex gap-1">
            <ActionButton icon={<PaperClipIcon className="h-4 w-4" />} label="Attach file" />
            <ActionButton icon={<PhotoIcon className="h-4 w-4" />} label="Add image" />
          </div>

          <button
            onClick={handleSend}
            disabled={!canSend}
            className={`flex h-8 w-8 items-center justify-center rounded-lg transition-all ${
              canSend
                ? 'bg-neutral-900 text-white hover:bg-neutral-700 active:scale-95 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-300'
                : 'cursor-not-allowed bg-neutral-200 text-neutral-400 dark:bg-neutral-700 dark:text-neutral-600'
            }`}
            aria-label="Send message"
          >
            {isLoading ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <ArrowUpIcon className="h-3.5 w-3.5 stroke-[2.5]" />
            )}
          </button>
        </div>
      </div>

      <p className="mt-2 text-center text-[11px] text-neutral-400 dark:text-neutral-600">
        Press <kbd className="rounded bg-neutral-100 px-1 font-mono text-[10px] dark:bg-neutral-800">Enter</kbd> to send,{' '}
        <kbd className="rounded bg-neutral-100 px-1 font-mono text-[10px] dark:bg-neutral-800">Shift+Enter</kbd> for newline
      </p>
    </div>
  )
}

function ActionButton({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button
      className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-[11px] text-neutral-400 transition-colors hover:bg-neutral-200 hover:text-neutral-700 dark:hover:bg-neutral-700 dark:hover:text-neutral-300"
      aria-label={label}
    >
      {icon}
      {label}
    </button>
  )
}
