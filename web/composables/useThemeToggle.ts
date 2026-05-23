import { useTheme } from 'vuetify'

const STORAGE_KEY = 'spl-web-theme'

export const useThemeToggle = () => {
  const theme = useTheme()
  const stored = useState<'light' | 'dark' | null>('theme-preference', () => null)

  const current = computed(() => theme.global.name.value as 'light' | 'dark')
  const isDark = computed(() => current.value === 'dark')

  const apply = (next: 'light' | 'dark') => {
    theme.global.name.value = next
    stored.value = next
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, next)
    }
  }

  const toggle = () => apply(isDark.value ? 'light' : 'dark')

  onMounted(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as 'light' | 'dark' | null
    if (saved === 'light' || saved === 'dark') {
      apply(saved)
    }
  })

  return { current, isDark, toggle, apply }
}
