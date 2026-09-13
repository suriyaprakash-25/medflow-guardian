import { Button } from './Button';
import { Dialog } from './Dialog';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDestructive?: boolean;
}

export function ConfirmModal({
  isOpen,
  title,
  description,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  onCancel,
  isDestructive = false,
}: ConfirmModalProps) {
  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => { if (!open) onCancel(); }}
      title={title}
      description={description}
      footer={(
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button variant="outline" onClick={onCancel}>{cancelText}</Button>
          <Button variant={isDestructive ? 'destructive' : 'default'} onClick={onConfirm}>{confirmText}</Button>
        </div>
      )}
    >
      <p className="text-sm leading-6 text-slate-600">Review the details above before continuing.</p>
    </Dialog>
  );
}
