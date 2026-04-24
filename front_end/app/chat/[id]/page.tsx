import { ChatPage } from '@/components/ChatPage'
import { mockConversations } from '@/lib/data'
import { notFound } from 'next/navigation'

interface Props {
  params: { id: string }
}

export default async function ChatRoute({ params }: Props) {
  const { id } = await params
  const conversation = mockConversations.find((c) => c.id === id)

  if (!conversation) notFound()

  return <ChatPage conversation={conversation} />
}
