'use client'

import { useState } from 'react'
import { ClipboardIcon, CheckIcon } from '@heroicons/react/24/outline'

interface CodeBlockProps {
  language: string
  code: string
}

export function CodeBlock({ language, code }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-3 overflow-hidden rounded-lg border border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-2 dark:border-neutral-700">
        <span className="font-mono text-[11px] text-neutral-400 dark:text-neutral-500">
          {language}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-[11px] text-neutral-400 transition-colors hover:text-neutral-700 dark:hover:text-neutral-300"
        >
          {copied ? (
            <>
              <CheckIcon className="h-3.5 w-3.5 text-green-500" />
              <span className="text-green-500">Copied</span>
            </>
          ) : (
            <>
              <ClipboardIcon className="h-3.5 w-3.5" />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Code */}
      <pre className="overflow-x-auto p-4 font-mono text-[12px] leading-relaxed text-neutral-800 dark:text-neutral-200">
        <code>{code}</code>
      </pre>
    </div>
  )
}
