import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

/** One button system: Petrol primary, bordered secondary, quiet ghost, Petrol text link. */
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors duration-150 ease-out disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-accent-600 text-surface hover:bg-accent-700',
        accent: 'bg-accent-600 text-surface hover:bg-accent-700',
        dark: 'bg-accent-600 text-surface hover:bg-accent-700',
        secondary: 'border border-line bg-surface text-ink hover:border-line-strong hover:bg-mist',
        ghost: 'text-ink-2 hover:bg-mist hover:text-ink',
        danger: 'border border-line bg-surface text-bad-ink hover:border-bad/40 hover:bg-bad-bg',
        link: 'h-auto px-0 text-accent-600 underline-offset-4 hover:text-accent-600 hover:underline',
      },
      size: { sm: 'h-8 px-3', md: 'h-9 px-3.5', lg: 'h-10 px-4', icon: 'size-9' },
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
