import { useEffect, useState } from 'react'

interface ShortcutAction {
  key: string
  description: string
  action: () => void
  ctrl?: boolean
  shift?: boolean
}

export function useKeyboardShortcuts(shortcuts: ShortcutAction[]) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't trigger when typing in input/textarea
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return

      for (const shortcut of shortcuts) {
        if (e.key === shortcut.key && !!e.ctrlKey === !!shortcut.ctrl && !!e.shiftKey === !!shortcut.shift) {
          e.preventDefault()
          shortcut.action()
          return
        }
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [shortcuts])
}

export function useShortcutHelp() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
      if (e.key === '?') {
        e.preventDefault()
        setVisible(v => !v)
      }
      if (e.key === 'Escape') setVisible(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return { visible, setVisible }
}
