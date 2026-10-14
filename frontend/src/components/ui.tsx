import { forwardRef } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Slot } from '@radix-ui/react-slot'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import * as SwitchPrimitive from '@radix-ui/react-switch'
import { cva } from 'class-variance-authority'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { LoaderCircle, X } from 'lucide-react'

const cn = (...inputs: Parameters<typeof clsx>) => twMerge(clsx(inputs))
const buttonVariants = cva('button', {
  variants: {
    variant: {
      primary: 'button-primary',
      secondary: 'button-secondary',
      ghost: 'button-ghost',
      danger: 'button-danger',
    },
    size: { normal: '', small: 'button-small', icon: 'button-icon' },
  },
  defaultVariants: { variant: 'primary', size: 'normal' },
})

// Local source components follow shadcn's composable Slot/Radix pattern.
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    asChild?: boolean
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'normal' | 'small' | 'icon'
    busy?: boolean
  }
>(function Button({ asChild, variant, size, className, busy, children, disabled, ...props }, ref) {
  const Comp = asChild ? Slot : 'button'
  return (
    <Comp
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...props}
    >
      {asChild ? (
        children
      ) : (
        <>
          {busy && <LoaderCircle size={16} className="spin" aria-hidden="true" />}
          {children}
        </>
      )}
    </Comp>
  )
})

export function Switch({
  id,
  checked,
  onCheckedChange,
  disabled,
}: {
  id: string
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  disabled?: boolean
}) {
  return (
    <SwitchPrimitive.Root
      id={id}
      className="switch"
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
    >
      <SwitchPrimitive.Thumb className="switch-thumb" />
    </SwitchPrimitive.Root>
  )
}

export function Dialog({
  trigger,
  title,
  description,
  children,
  open,
  onOpenChange,
}: {
  trigger?: ReactNode
  title: string
  description?: string
  children: ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      {trigger && <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger>}
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="dialog-overlay" />
        <DialogPrimitive.Content
          className="dialog-content"
          {...(!description ? { 'aria-describedby': undefined } : {})}
        >
          <div className="dialog-heading">
            <DialogPrimitive.Title>{title}</DialogPrimitive.Title>
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close dialog">
                <X size={20} aria-hidden="true" />
              </Button>
            </DialogPrimitive.Close>
          </div>
          {description && (
            <DialogPrimitive.Description className="muted">
              {description}
            </DialogPrimitive.Description>
          )}
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: 'neutral' | 'good' | 'warning' | 'danger' | 'blue'
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

export function ErrorNotice({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <div role="alert" className="notice notice-error">
      <strong>We couldn’t load this.</strong>
      <p>{error instanceof Error ? error.message : 'Something went wrong. Please try again.'}</p>
      {retry && (
        <Button variant="secondary" size="small" onClick={retry}>
          Try again
        </Button>
      )}
    </div>
  )
}

export function Loading({ label = 'Loading campus data' }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <LoaderCircle className="spin" size={24} aria-hidden="true" />
      <span>{label}…</span>
    </div>
  )
}
