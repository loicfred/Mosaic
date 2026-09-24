import * as T from '@radix-ui/react-tabs'
import { cn } from '@/lib/cn'

export const Tabs = T.Root
export const TabsContent = T.Content

export function TabsList({ className, ...p }: T.TabsListProps) {
  return (
    <T.List
      className={cn('inline-flex max-w-full gap-1 overflow-x-auto rounded-full border border-line bg-surface p-1 shadow-card', className)}
      {...p}
    />
  )
}

export function TabsTrigger({ className, ...p }: T.TabsTriggerProps) {
  return (
    <T.Trigger
      className={cn(
        'shrink-0 whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium text-ink-2 transition-colors hover:text-ink data-[state=active]:bg-accent-600 data-[state=active]:text-white',
        className,
      )}
      {...p}
    />
  )
}
