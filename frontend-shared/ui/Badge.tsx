import React from 'react'

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'
}

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className = '', variant = 'default', ...props }, ref) => {
    let variantStyles = ''
    switch (variant) {
      case 'secondary': variantStyles = 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80'; break
      case 'destructive': variantStyles = 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80'; break
      case 'outline': variantStyles = 'text-foreground'; break
      case 'success': variantStyles = 'border-transparent bg-emerald-500 text-white hover:bg-emerald-600'; break
      case 'warning': variantStyles = 'border-transparent bg-amber-500 text-white hover:bg-amber-600'; break
      default: variantStyles = 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80'; break
    }

    const baseStyles = 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2'

    return (
      <div ref={ref} className={`${baseStyles} ${variantStyles} ${className}`} {...props} />
    )
  }
)
Badge.displayName = "Badge"
