import { Activity, LayoutDashboard, MessageCircle, Settings, Sparkles, Wallet2 } from 'lucide-react'
import type { ComponentType } from 'react'

export interface NavItem {
  to: string
  label: string
  icon: ComponentType<{ className?: string }>
}

export const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/copilot', label: 'AI Copilot', icon: MessageCircle },
  { to: '/opportunities', label: 'Opportunities', icon: Sparkles },
  { to: '/transactions', label: 'Transactions', icon: Wallet2 },
  { to: '/activity', label: 'Activity', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
]
