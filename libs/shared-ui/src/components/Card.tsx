import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@edulution-io/ui-kit';
import { CardContent as SHCardContent, CardSH as SHCard } from './CardSH';

const cardVariants = cva('shadow-lg', {
  variants: {
    variant: {
      collaboration: 'border-primary border-4',
      organisation: 'border-ciLightBlue border-4',
      infrastructure: 'border-ciLightGreen border-4',
      security: 'gradient-box',
      modal:
        'border-4 border-white fixed left-[50%] top-[40%] max-h-[85vh] w-[90vw] max-w-[450px] translate-x-[-50%] translate-y-[-50%] rounded-xl bg-white p-[25px] text-foreground',
      text: 'border-accent border-3 bg-glass backdrop-blur-lg bg-opacity-20 inset-2 overflow-auto scrollbar-none hover:scrollbar-thin',
      dialog: 'bg-glass border-white dark:border-black transition-transform duration-300 hover:scale-105',
      grid: 'border border-accent hover:shadow-md cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary transition-[border-color,background-color,box-shadow,transform] duration-200 hover:scale-[103%]',
      gridSelected:
        'border-primary bg-primary/5 hover:shadow-md cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary transition-[border-color,background-color,box-shadow,transform] duration-200 hover:scale-[103%]',
    },
  },
  defaultVariants: {
    variant: 'collaboration',
  },
});

type CardProps = React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof cardVariants>;

const Card = React.forwardRef<HTMLDivElement, CardProps>(({ className, variant, ...props }, ref) => {
  Card.displayName = 'Card';

  return (
    <SHCard
      ref={ref}
      className={cn(cardVariants({ variant }), 'border-solid', className)}
      {...props}
    />
  );
});

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref): JSX.Element => {
    CardContent.displayName = 'CardContent';
    return (
      <SHCardContent
        ref={ref}
        className={cn('p-[20px]', className)}
        {...props}
      />
    );
  },
);

export { Card, CardContent };
