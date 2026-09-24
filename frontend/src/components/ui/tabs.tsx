import * as T from '@radix-ui/react-tabs'
import { cn } from '@/lib/cn'

export const Tabs = T.Root
export const TabsContent = T.Content

/** Underlined tabs on a hairline: the selected tab is Petrol, the rest stay neutral. */
export function TabsList({ className, ...p }: T.TabsListProps) {
  return <T.List className={cn('flex max-w-full gap-6 overflow-x-auto border-b border-line', className)} {...p} />
}

export function TabsTrigger({ className, ...p }: T.TabsTriggerProps) {
  return (
    <T.Trigger
      className={cn(
        '-mb-px shrink-0 whitespace-nowrap border-b-2 border-transparent pb-2.5 pt-1 text-sm font-medium text-ink-3 transition-colors duration-150 hover:text-ink data-[state=active]:border-accent-600 data-[state=active]:text-accent-600',
        className,
      )}
      {...p}
    />
  )
}
