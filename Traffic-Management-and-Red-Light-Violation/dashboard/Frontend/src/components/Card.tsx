import { ReactNode } from 'react';

interface Props {
  title?: string;
  className?: string;
  children: ReactNode;
}
export default function Card({ title, className='', children }: Props) {
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-card p-6 ${className}`}>
      {title && <h3 className="text-lg mb-4 text-center">{title}</h3>}
      {children}
    </div>
  );
}
