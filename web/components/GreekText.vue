<script setup lang="ts">
/**
 * Wraps polytonic Greek strings so they render in the SBL Greek font.
 *
 * Usage:
 *   <GreekText>πίστις, ἐλπίς, ἀγάπη</GreekText>
 *
 * Applies .text-grc (defined in assets/styles/globals.css). Theme-agnostic;
 * the font is self-hosted at /fonts/SBLGreek.woff2 and is loaded with
 * `font-display: swap` so initial paint isn't blocked.
 */
defineProps<{ ariaLabel?: string }>()
</script>

<template>
  <span class="text-grc" :aria-label="ariaLabel" data-testid="greek-text">
    <slot />
  </span>
</template>
