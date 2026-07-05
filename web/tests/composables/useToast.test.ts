import { describe, expect, it } from 'vitest'
import { useToast } from '~~/composables/useToast'

describe('useToast', () => {
  it('notify shows a success message by default', () => {
    const { toast, notify } = useToast()
    notify('Created “righteousness”')
    expect(toast.value.show).toBe(true)
    expect(toast.value.text).toBe('Created “righteousness”')
    expect(toast.value.color).toBe('success')
  })

  it('notify can flag an error', () => {
    const { toast, notify } = useToast()
    notify('already exists', 'error')
    expect(toast.value.color).toBe('error')
    expect(toast.value.text).toBe('already exists')
  })

  it('shares one snackbar across callers (singleton state)', () => {
    const a = useToast()
    const b = useToast()
    a.notify('from a')
    expect(b.toast.value.text).toBe('from a')
  })
})
