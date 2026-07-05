/**
 * App-wide transient feedback (snackbar). One `<v-snackbar>` in the reader
 * layout renders whatever `notify` sets, so any component/page can confirm a
 * write ("Created 'righteousness'") or surface a failure without wiring its own
 * UI. State is `useState` (SSR-safe singleton) so every caller shares the one
 * snackbar.
 */
export type ToastColor = 'success' | 'error' | 'info'

export interface ToastState {
  show: boolean
  text: string
  color: ToastColor
}

export const useToast = () => {
  const toast = useState<ToastState>('toast', () => ({
    show: false,
    text: '',
    color: 'success',
  }))

  const notify = (text: string, color: ToastColor = 'success'): void => {
    // Reassign so the watcher fires even for an identical consecutive message
    // (e.g. two saves in a row) — toggling `show` alone would not re-trigger.
    toast.value = { show: true, text, color }
  }

  return { toast, notify }
}
