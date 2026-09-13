import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'default', size = 'default', type = 'button', ...props }, ref) => {
    let variantStyles = '';
    switch (variant) {
      case 'destructive': variantStyles = 'bg-destructive text-destructive-foreground hover:bg-destructive/90'; break;
      case 'outline': variantStyles = 'border border-input bg-background hover:bg-accent hover:text-accent-foreground'; break;
      case 'secondary': variantStyles = 'bg-secondary text-secondary-foreground hover:bg-secondary/80'; break;
      case 'ghost': variantStyles = 'hover:bg-accent hover:text-accent-foreground'; break;
      case 'link': variantStyles = 'text-primary underline-offset-4 hover:underline'; break;
      default: variantStyles = 'bg-primary text-primary-foreground hover:bg-primary/90'; break;
    }

    let sizeStyles = '';
    switch (size) {
      case 'sm': sizeStyles = 'min-h-11 rounded-md px-3'; break;
      case 'lg': sizeStyles = 'min-h-12 rounded-md px-8'; break;
      case 'icon': sizeStyles = 'h-11 w-11'; break;
      default: sizeStyles = 'min-h-11 px-4 py-2'; break;
    }

    const baseStyles = 'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-semibold ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';

    return (
      <button
        ref={ref}
        type={type}
        className={`${baseStyles} ${variantStyles} ${sizeStyles} ${className}`}
        {...props}
      />
    );
  },
);
Button.displayName = 'Button';
