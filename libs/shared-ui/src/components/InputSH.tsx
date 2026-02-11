import * as React from 'react';
import { cn } from '@edulution-io/ui-kit';

const InputSH = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        'h-10 w-full rounded-lg border bg-card px-3 text-card-foreground transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium focus:outline-none disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
InputSH.displayName = 'InputSH';

export { InputSH };
