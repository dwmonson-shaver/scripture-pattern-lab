import { useTheme } from 'vuetify'

const STORAGE_KEY = 'spl-web-theme'

// The reader's identity is the study-edition 'parchment' theme (DEC-152);
// 'dark' is the retained alternate. The toggle swaps between the two.
type ThemeName = 'parchment' | 'dark'

export const useThemeToggle = () => {
  const theme = useTheme()
  const stored = useState<ThemeName | null>('theme-preference', () => null)

  const current = computed(() => theme.global.name.value as ThemeName)
  const isDark = computed(() => current.value === 'dark')

  const apply = (next: ThemeName) => {
    theme.global.name.value = next
    stored.value = next
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, next)
    }
  }

  const toggle = () => apply(isDark.value ? 'parchment' : 'dark')

  onMounted(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as ThemeName | null
    if (saved === 'parchment' || saved === 'dark') {
      apply(saved)
    }
  })

  return { current, isDark, toggle, apply }
}
