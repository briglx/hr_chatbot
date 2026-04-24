import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Sidebar } from '@/components/Sidebar'
import { mockConversations, mockUser } from '@/lib/data'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ChatApp',
  description: 'AI-powered chat application',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-white antialiased dark:bg-neutral-950`}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar conversations={mockConversations} user={mockUser} />
          <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
        </div>
      </body>
    </html>
  )
}
