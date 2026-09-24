import * as T from '@radix-ui/react-tabs'
import { cn } from '@/lib/cn'

export const Tabs = T.Root
export const TabsContent = T.Content

export function TabsList({ className, ...p }: T.TabsListProps) {
  return (
    <T.List
      className={cn('inline-flex max-w-full gap-1 overflow-x-auto rounded-lg border border-line bg-surface-2 p-1', className)}
      {...p}
    />
  )
}

export function TabsTrigger({ className, ...p }: T.TabsTriggerProps) {
  return (
    <T.Trigger
      className={cn(
        'shrink-0 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium text-ink-3 hover:text-ink data-[state=active]:bg-surface data-[state=active]:text-ink data-[state=active]:shadow-sm',
        className,
      )}
      {...p}
    />
  )
}
