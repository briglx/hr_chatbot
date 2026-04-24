'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { PlusIcon, ShareIcon, DotsVerticalIcon } from '@heroicons/react/24/outline'
import { Conversation, User } from '@/lib/types'
import { groupConversationsByDate } from '@/lib/data'

interface SidebarProps {
  conversations: Conversation[]
  user: User
}

export function Sidebar({ conversations, user }: SidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const groups = groupConversationsByDate(conversations)

  const planLabel: Record<User['plan'], string> = {
    free: 'Free plan',
    pro: 'Pro plan',
    team: 'Team plan',
  }

  return (
    <aside className="flex h-full w-60 flex-shrink-0 flex-col gap-2 border-r border-neutral-200 bg-neutral-50 p-3 dark:border-neutral-800 dark:bg-neutral-900">
      {/* Header */}
      <div className="flex items-center justify-between px-1 pb-2">
        <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
          ChatApp
        </span>
      </div>

      {/* New chat */}
      <button
        onClick={() => router.push('/chat')}
        className="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700"
      >
        <PlusIcon className="h-4 w-4 opacity-60" />
        New chat
      </button>

      {/* Conversation groups */}
      <nav className="flex flex-1 flex-col gap-4 overflow-y-auto">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="mb-1 px-2 text-[11px] font-medium uppercase tracking-wider text-neutral-400 dark:text-neutral-600">
              {group.label}
            </p>
            <ul className="flex flex-col gap-0.5">
              {group.items.map((conv) => {
                const isActive = pathname === `/chat/${conv.id}`
                return (
                  <li key={conv.id}>
                    <Link
                      href={`/chat/${conv.id}`}
                      className={`block truncate rounded-md px-3 py-1.5 text-sm transition-colors ${
                        isActive
                          ? 'bg-white font-medium text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100'
                          : 'text-neutral-600 hover:bg-white hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200'
                      }`}
                    >
                      {conv.title}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="flex items-center gap-2 border-t border-neutral-200 pt-3 dark:border-neutral-800">
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 text-[11px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
          {user.avatarInitials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">
            {user.name}
          </p>
          <p className="text-[11px] text-neutral-400 dark:text-neutral-600">
            {planLabel[user.plan]}
          </p>
        </div>
      </div>
    </aside>
  )
}
