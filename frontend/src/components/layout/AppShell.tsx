import clsx from 'clsx'
import { NavLink, Outlet } from 'react-router-dom'
import { ConnectWalletButton } from '@/components/wallet/ConnectWalletButton'
import { navItems } from '@/components/layout/nav'

function Logo() {
  return (
    <div className="flex items-center gap-2 px-1">
      <div className="flex size-8 items-center justify-center rounded-lg bg-[var(--color-accent)] text-sm font-bold text-black">
        N
      </div>
      <span className="text-sm font-semibold tracking-tight text-[var(--color-text-primary)]">NexaPilot</span>
    </div>
  )
}

export function AppShell() {
  return (
    <div className="flex min-h-dvh bg-[var(--color-canvas)]">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-[var(--color-border)] px-4 py-6 lg:flex">
        <Logo />
        <nav className="mt-8 flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-[var(--color-surface-raised)] text-[var(--color-text-primary)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]',
                )
              }
            >
              <item.icon className="size-4.5" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3 sm:px-6">
          <div className="lg:hidden">
            <Logo />
          </div>
          <div className="hidden lg:block" />
          <ConnectWalletButton />
        </header>

        <main className="flex-1 overflow-y-auto px-4 pb-24 pt-5 sm:px-6 lg:pb-8">
          <div className="mx-auto w-full max-w-5xl">
            <Outlet />
          </div>
        </main>

        {/* Mobile bottom nav */}
        <nav className="fixed inset-x-0 bottom-0 z-10 flex border-t border-[var(--color-border)] bg-[var(--color-surface)]/95 backdrop-blur lg:hidden">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-medium',
                  isActive ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]',
                )
              }
            >
              <item.icon className="size-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
