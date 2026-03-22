import { useShortcutHelp } from '../hooks/useKeyboardShortcuts'

const SHORTCUTS = [
  { key: 'Tab', description: 'Move to next field needing review' },
  { key: 'Enter', description: 'Approve current field' },
  { key: 'E', description: 'Edit current field' },
  { key: 'Shift+Enter', description: 'Approve all & continue' },
  { key: 'Esc', description: 'Cancel edit / close dialog' },
  { key: '?', description: 'Toggle this help' },
]

export default function ShortcutHelp() {
  const { visible, setVisible } = useShortcutHelp()

  if (!visible) return null

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setVisible(false)}>
      <div className="bg-white rounded-2xl shadow-xl p-6 max-w-md w-full" onClick={e => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Keyboard Shortcuts</h3>
        <div className="space-y-2">
          {SHORTCUTS.map(s => (
            <div key={s.key} className="flex justify-between text-xs">
              <span className="text-gray-600">{s.description}</span>
              <kbd className="px-2 py-0.5 bg-gray-100 rounded text-gray-700 font-mono text-[10px]">{s.key}</kbd>
            </div>
          ))}
        </div>
        <button onClick={() => setVisible(false)} className="mt-4 w-full px-3 py-2 bg-gray-100 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-200">Close</button>
      </div>
    </div>
  )
}
