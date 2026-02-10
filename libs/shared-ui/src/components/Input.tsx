import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@edulution-io/ui-kit';
import { InputSH } from './InputSH';

const inputVariants = cva(
  'h-10 w-full rounded-lg px-3 text-p transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium focus:outline-none disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'dark:bg-accent border border-accent-light bg-white text-background placeholder:text-p',
        dialog: 'dark:bg-accent border border-accent-light bg-white text-background placeholder:text-p',
        login:
          'border-[1px] border-gray-300 bg-white text-black shadow-md placeholder:text-p focus:border-gray-600 focus:bg-white focus:placeholder-muted',
        lightGrayDisabled: 'bg-ciDarkGreyDisabled text-secondary placeholder:text-p',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

type InputProps = React.InputHTMLAttributes<HTMLInputElement> &
  VariantProps<typeof inputVariants> & {
    icon?: React.ReactNode;
  };

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant, icon, ...props }, ref) => {
    Input.displayName = 'Input';

    const inputElement = (
      <InputSH
        ref={ref}
        className={cn(inputVariants({ variant }), className)}
        {...props}
      />
    );

    if (!icon) {
      return inputElement;
    }

    return (
      <div className="relative w-full">
        {inputElement}
        <div className="absolute inset-y-0 right-0 flex items-center pr-3">{icon}</div>
      </div>
    );
  },
);

export { Input, inputVariants };
