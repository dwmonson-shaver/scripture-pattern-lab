/**
 * Multi-select concept highlight state for the reader (spec: several concepts
 * can be highlighted at once; non-selected marks dim but KEEP their underline).
 *
 * Pure UI state — no fetch, no persistence. The reader page owns one instance
 * and feeds the selected-name set to ChapterView (which applies `.on` to
 * matching marks and a `has-sel` class to dim the rest) and to ConceptLibrary
 * (which shows the `.sel` row state). Component-local; no Pinia (DEC: state mgmt).
 */
export const useConceptSelection = () => {
  const selected = ref<Set<string>>(new Set())
  // The most-recently-activated concept — drives which one the panel details.
  const lastActive = ref<string | null>(null)

  const hasSelection = computed(() => selected.value.size > 0)

  const isSelected = (name: string): boolean => selected.value.has(name)

  /** Toggle a concept in/out of the highlight set (③ click again → off). */
  const toggle = (name: string): void => {
    const next = new Set(selected.value)
    if (next.has(name)) {
      next.delete(name)
      if (lastActive.value === name) {
        const arr = Array.from(next)
        lastActive.value = arr.length ? arr[arr.length - 1] : null
      }
    } else {
      next.add(name)
      lastActive.value = name
    }
    selected.value = next
  }

  /** Ensure a concept is highlighted (used when activating a mark's concept). */
  const add = (name: string): void => {
    if (!selected.value.has(name)) {
      const next = new Set(selected.value)
      next.add(name)
      selected.value = next
    }
    lastActive.value = name
  }

  const clear = (): void => {
    selected.value = new Set()
    lastActive.value = null
  }

  return { selected, lastActive, hasSelection, isSelected, toggle, add, clear }
}
