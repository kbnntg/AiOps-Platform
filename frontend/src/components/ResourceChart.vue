<template>
  <div ref="chartRef" :style="{ height, width: '100%' }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] },
  height: { type: String, default: '300px' },
})

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!chartRef.value || !chart) return
  const series = (props.data as any[]).map((item: any) => ({
    name: item.metric?.instance || 'unknown',
    type: 'line',
    smooth: true,
    showSymbol: false,
    areaStyle: { opacity: 0.1 },
    data: (item.values || []).map((v: any) => [Number(v[0]) * 1000, Number(v[1])]),
  }))
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { show: series.length > 1, bottom: 0 },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series,
  })
}

onMounted(() => {
  if (chartRef.value) { chart = echarts.init(chartRef.value); render() }
})
watch(() => props.data, render, { deep: true })
onBeforeUnmount(() => chart?.dispose())
</script>