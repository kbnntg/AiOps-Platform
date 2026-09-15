<template>
  <transition name="app-bg-fade">
    <div v-if="store.hasBackground" class="app-bg" aria-hidden="true">
      <div class="app-bg__image" :style="store.backgroundStyle"></div>
      <div class="app-bg__overlay" :style="store.overlayStyle"></div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { useAppearanceStore } from '@/stores/appearance'

const store = useAppearanceStore()
</script>

<style scoped>
/* 固定在视口底层，z-index: -1 保证永远位于所有页面内容之后 */
.app-bg {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  pointer-events: none;
}

.app-bg__image {
  position: absolute;
  inset: 0;
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
  transition: filter 0.3s ease, transform 0.3s ease;
  will-change: transform, filter;
}

.app-bg__overlay {
  position: absolute;
  inset: 0;
  transition: background 0.3s ease;
}

.app-bg-fade-enter-active,
.app-bg-fade-leave-active {
  transition: opacity 0.35s ease;
}
.app-bg-fade-enter-from,
.app-bg-fade-leave-to {
  opacity: 0;
}
</style>
