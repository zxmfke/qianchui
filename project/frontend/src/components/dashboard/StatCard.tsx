import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  trend?: number;
  icon: LucideIcon;
  color?: 'indigo' | 'emerald' | 'amber' | 'cyan';
}

const colorMap = {
  indigo: {
    bg: 'bg-indigo-500/10',
    border: 'border-indigo-500/30',
    icon: 'text-indigo-400',
    gradient: 'from-indigo-500/20 to-indigo-600/5',
  },
  emerald: {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    icon: 'text-emerald-400',
    gradient: 'from-emerald-500/20 to-emerald-600/5',
  },
  amber: {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    icon: 'text-amber-400',
    gradient: 'from-amber-500/20 to-amber-600/5',
  },
  cyan: {
    bg: 'bg-cyan-500/10',
    border: 'border-cyan-500/30',
    icon: 'text-cyan-400',
    gradient: 'from-cyan-500/20 to-cyan-600/5',
  },
};

export default function StatCard({ title, value, trend, icon: Icon, color = 'indigo' }: StatCardProps) {
  const c = colorMap[color];

  return (
    <div className={cn('glass-card p-4 bg-gradient-to-br', c.gradient)}>
      <div className="flex items-start justify-between mb-2">
        <div className={cn('p-1.5 rounded-lg', c.bg, 'border', c.border)}>
          <Icon className={cn('w-4 h-4', c.icon)} />
        </div>
        {trend != null && (
          <span
            className={cn(
              'text-xs font-medium px-2 py-0.5 rounded-full',
              trend >= 0
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-red-500/20 text-red-400',
            )}
          >
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </span>
        )}
      </div>
      <p className="text-xl font-bold text-slate-100">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{title}</p>
    </div>
  );
}
