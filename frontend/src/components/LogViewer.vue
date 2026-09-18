<template>
  <div class="log-viewer">
    <pre class="log-content">{{ logs || '暂无日志' }}</pre>
  </div>
</template>

<script setup lang="ts">
defineProps({ logs: { type: String, default: '' } })
</script>

<style scoped>
.log-viewer { background: #1e1e1e; color: #d4d4d4; border-radius: 4px; padding: 16px; max-height: 600px; overflow: auto; }
.log-content { margin: 0; font-family: Consolas, monospace; font-size: 12px; line-height: 1.6; white-space: pre-wrap; word-break: break-all; }
</style>