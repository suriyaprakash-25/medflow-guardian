
import { Button } from './Button'

interface ConfirmModalProps {
  isOpen: boolean
  title: string
  description: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
  isDestructive?: boolean
}

export function ConfirmModal({
  isOpen,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  onConfirm,
  onCancel,
  isDestructive = false
}: ConfirmModalProps) {
  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center animate-in fade-in"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)', position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}
    >
      <div 
        className="w-full rounded-lg p-6 shadow-lg animate-in zoom-in-95 border border-slate-200"
        style={{ backgroundColor: '#ffffff', maxWidth: '450px' }}
      >
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm text-slate-500">{description}</p>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onCancel} className="text-slate-700">
            {cancelText}
          </Button>
          <Button 
            variant={isDestructive ? "destructive" : "default"} 
            onClick={onConfirm}
            className="text-white border-none"
            style={{ backgroundColor: isDestructive ? '#ef4444' : '#2563eb' }}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </div>
  )
}
