import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-[color,background-color,border-color,transform] duration-150 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-accent-600 text-white hover:bg-accent-700 active:translate-y-px',
        accent: 'bg-accent-600 text-white hover:bg-accent-700 active:translate-y-px',
        dark: 'bg-brand-900 text-white hover:bg-brand-700 active:translate-y-px',
        secondary: 'border border-line-strong bg-surface text-ink hover:bg-surface-2',
        ghost: 'text-ink-2 hover:bg-brand-50 hover:text-ink',
        danger: 'border border-bad/30 bg-surface text-bad-ink hover:bg-bad-bg',
        link: 'h-auto px-0 text-accent-700 underline-offset-4 hover:underline',
      },
      size: { sm: 'h-8 px-3 text-xs', md: 'h-9 px-4', lg: 'h-10 px-5', icon: 'size-9' },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild, ...props }, ref) => {
  const Comp = asChild ? Slot : 'button'
  return <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
})
Button.displayName = 'Button'
