import { Conversation, User } from './types'

export const mockUser: User = {
  id: 'user-1',
  name: 'Jamie D.',
  email: 'jamie@example.com',
  plan: 'pro',
  avatarInitials: 'JD',
}

const now = new Date()
const yesterday = new Date(now)
yesterday.setDate(yesterday.getDate() - 1)
const lastWeek = new Date(now)
lastWeek.setDate(lastWeek.getDate() - 5)

export const mockConversations: Conversation[] = [
    {
      id: 'conv-1',
      title: 'Updating our PTO policy',
      createdAt: now,
      updatedAt: now,
      messages: [
        {
          id: 'msg-1',
          role: 'user',
          content: 'We want to move from a traditional accrual PTO model to an unlimited PTO policy. What are the key considerations before making this change?',
          createdAt: now,
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: `Moving to unlimited PTO is a significant cultural shift. Here are the key areas to address before rolling it out:
  
  **Policy Design**
  - Define what "unlimited" actually means — most companies set a soft minimum (e.g. 15 days/year) to prevent employees from taking too little
  - Clarify approval process: does a manager still need to approve time off?
  - Decide how to handle busy seasons or blackout periods
  
  **Legal & Compliance**
  - In some states (e.g. California), accrued PTO is treated as earned wages. Switching to unlimited removes the accrual liability, but you must carefully handle any banked hours employees currently hold
  - Update your employee handbook and have legal review the new policy language
  
  **Cultural Risk**
  - Without clear norms, employees — especially high performers — often take *less* time off under unlimited PTO due to ambiguity
  - Manager training is critical: they need to actively encourage time off, not just permit it
  
  **Transition Plan**
  - Will you pay out existing accrued balances? This is often required legally and always recommended for trust
  - Set an effective date and communicate at least 60 days in advance
  
  Would you like a sample policy template or a communication plan for the rollout?`,
          createdAt: now,
        },
        {
          id: 'msg-3',
          role: 'user',
          content: 'Yes, can you draft a short policy summary we could include in the handbook?',
          createdAt: now,
        },
        {
          id: 'msg-4',
          role: 'assistant',
          content: `Here's a concise handbook-ready policy summary:
  
  ---
  
  **Flexible Time Off Policy**
  
  We trust our employees to manage their time and take the rest they need to perform at their best. Full-time employees are eligible for flexible, unlimited paid time off (PTO) with manager approval.
  
  *Guidelines:*
  - We encourage a minimum of 15 days off per year, including personal days and vacation
  - Requests should be submitted at least [X] days in advance for planned absences
  - Time off during company blackout periods (e.g. fiscal year-end) requires VP approval
  - Flexible PTO does not accrue and has no cash value upon separation
  
  This policy is built on mutual trust. Managers are expected to lead by example and actively support their teams in taking regular, meaningful time away from work.
  
  ---
  
  Want me to adjust the tone, add a section on sick leave, or tailor this for a specific jurisdiction?`,
          createdAt: now,
        },
      ],
    },
    {
      id: 'conv-2',
      title: 'Writing a performance improvement plan',
      createdAt: now,
      updatedAt: now,
      messages: [
        {
          id: 'msg-5',
          role: 'user',
          content: 'I need to put a direct report on a PIP. They are missing deadlines consistently and communication with the team has been poor. Where do I start?',
          createdAt: now,
        },
        {
          id: 'msg-6',
          role: 'assistant',
          content: `A well-structured PIP protects both the employee and the company. Here's how to approach it:
  
  **Before You Write Anything**
  - Document specific incidents: dates, missed deadlines, and any prior verbal feedback you've given. Vague PIPs are hard to enforce and easy to dispute
  - Loop in HR before the conversation — they should review the plan before it's delivered
  
  **PIP Structure**
  1. **Statement of concern** — factual, non-emotional description of the performance gap
  2. **Expected standard** — what "good" looks like in this role
  3. **Specific, measurable goals** — e.g. "deliver weekly status report by Friday 5pm for the next 8 weeks"
  4. **Support provided** — what you'll do to help (1:1s, resources, training)
  5. **Check-in schedule** — typically bi-weekly formal reviews
  6. **Timeline** — usually 30, 60, or 90 days
  7. **Consequences** — clearly state what happens if goals are not met
  
  **The Conversation**
  - Deliver it in a private setting with an HR rep present
  - Frame it as a path to success, not a precursor to termination — even if it may be
  
  Would you like me to draft a PIP template based on the specific issues you described?`,
          createdAt: now,
        },
      ],
    },
    {
      id: 'conv-3',
      title: 'Structuring our onboarding program',
      createdAt: now,
      updatedAt: now,
      messages: [
        {
          id: 'msg-7',
          role: 'user',
          content: 'What needs to be done for new employees?',
          createdAt: now,
        },
        {
          id: 'msg-8',
          role: 'assistant',
          content: "A well-structured PIP protects both the employee and the company. Here's how to approach it:",
          createdAt: now,
        }
      ],
    },
    {
      id: 'conv-4',
      title: 'Handling a harassment complaint',
      createdAt: yesterday,
      updatedAt: yesterday,
      messages: [],
    },
    {
      id: 'conv-5',
      title: 'Compensation benchmarking process',
      createdAt: yesterday,
      updatedAt: yesterday,
      messages: [],
    },
    {
      id: 'conv-6',
      title: 'Reducing employee turnover',
      createdAt: lastWeek,
      updatedAt: lastWeek,
      messages: [],
    },
    {
      id: 'conv-7',
      title: 'FMLA eligibility questions',
      createdAt: lastWeek,
      updatedAt: lastWeek,
      messages: [],
    },
  ]


export const mockConversations2: Conversation[] = [
  {
    id: 'conv-1',
    title: 'Next.js App Router setup',
    createdAt: now,
    updatedAt: now,
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        content: 'How do I set up a Next.js 14 project with the App Router and TypeScript?',
        createdAt: now,
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: `To scaffold a new Next.js 14 project with App Router and TypeScript, run:

\`\`\`bash
npx create-next-app@latest my-app \\
  --typescript \\
  --tailwind \\
  --app \\
  --eslint
\`\`\`

This sets up TypeScript, Tailwind CSS, and the App Router by default. Your \`app/\` directory will contain \`layout.tsx\` and \`page.tsx\` as entry points.`,
        createdAt: now,
      },
    ],
  },
  {
    id: 'conv-2',
    title: 'React Server Components',
    createdAt: now,
    updatedAt: now,
    messages: [],
  },
  {
    id: 'conv-3',
    title: 'Tailwind dark mode config',
    createdAt: now,
    updatedAt: now,
    messages: [],
  },
  {
    id: 'conv-4',
    title: 'Prisma schema design',
    createdAt: yesterday,
    updatedAt: yesterday,
    messages: [],
  },
  {
    id: 'conv-5',
    title: 'API route authentication',
    createdAt: yesterday,
    updatedAt: yesterday,
    messages: [],
  },
  {
    id: 'conv-6',
    title: 'Deployment to Vercel',
    createdAt: lastWeek,
    updatedAt: lastWeek,
    messages: [],
  },
  {
    id: 'conv-7',
    title: 'Edge runtime vs Node.js',
    createdAt: lastWeek,
    updatedAt: lastWeek,
    messages: [],
  },
]

export function groupConversationsByDate(conversations: Conversation[]) {
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfYesterday = new Date(startOfToday)
  startOfYesterday.setDate(startOfYesterday.getDate() - 1)
  const sevenDaysAgo = new Date(startOfToday)
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'Last 7 days', items: [] },
    { label: 'Older', items: [] },
  ]

  for (const conv of conversations) {
    const date = new Date(conv.updatedAt)
    if (date >= startOfToday) {
      groups[0].items.push(conv)
    } else if (date >= startOfYesterday) {
      groups[1].items.push(conv)
    } else if (date >= sevenDaysAgo) {
      groups[2].items.push(conv)
    } else {
      groups[3].items.push(conv)
    }
  }

  return groups.filter((g) => g.items.length > 0)
}
