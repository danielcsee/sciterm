import { useEffect, useRef } from 'react'

/**
 * Open a native `<dialog>` as a modal on mount, and route Escape to `onClose`.
 *
 * Same approach as `AccessCodeModal`: `showModal()` rather than the `open`
 * attribute, because only the modal form gets the top layer, the backdrop and
 * the focus trap. The browser's own close on Escape is cancelled so React
 * state stays the one thing deciding whether the dialog is shown.
 */
export function useModalDialog(onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (!dialog.open) dialog.showModal()
    const handleCancel = (event: Event) => {
      event.preventDefault()
      onClose()
    }
    dialog.addEventListener('cancel', handleCancel)
    return () => dialog.removeEventListener('cancel', handleCancel)
  }, [onClose])

  return ref
}

/**
 * Enter submits, explicitly: implicit submission does not fire for inputs
 * inside a modal `<dialog>` (verified in `AccessCodeModal`).
 */
export function submitOnEnter(event: React.KeyboardEvent, submit: () => Promise<void>) {
  if (event.key !== 'Enter') return
  event.preventDefault()
  void submit()
}
