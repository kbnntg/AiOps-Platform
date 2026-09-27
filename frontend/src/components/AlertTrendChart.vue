<template>
  <div ref="chartRef" :style="{ height, width: '100%' }"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

/**
 * 告警趋势柱状图
 * 数据来自 GET /api/alerts/metrics 的 trend 字段：[{ day: '2024-05-05', count: 3 }]
 */
const props = defineProps({
  data: { type: Array, default: () => [] },
  height: { type: String, default: '240px' },
})

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

interface TrendPoint {
  day: string
  count: number
}

/** 补齐近 7 天：后端只返回有告警的日期，缺失的日期要在前端补 0 */
function fillMissingDays(raw: TrendPoint[]): TrendPoint[] {
  const map = new Map<string, number>()
  raw.forEach((item) => {
    if (!item?.day) return
    map.set(String(item.day).slice(0, 10), Number(item.count) || 0)
  })

  const days: TrendPoint[] = []
  const today = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i)
    const pad = (n: number) => (n < 10 ? `0${n}` : String(n))
    const key = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    days.push({ day: key, count: map.get(key) ?? 0 })
  }

  // 如果后端返回了 7 天以外的日期（时区/历史数据），一并展示，避免丢数据
  raw.forEach((item) => {
    const key = String(item?.day || '').slice(0, 10)
    if (key && !days.some((d) => d.day === key)) {
      days.push({ day: key, count: Number(item.count) || 0 })
    }
  })
  return days
}

function render() {
  if (!chart) return
  const points = fillMissingDays(props.data as TrendPoint[])
  const max = Math.max(1, ...points.map((p) => p.count))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const item = Array.isArray(params) ? params[0] : params
        return `${item.name}<br/>告警 ${item.value} 条`
      },
    },
    grid: { left: 40, right: 20, top: 24, bottom: 30 },
    xAxis: {
      type: 'category',
      data: points.map((p) => p.day.slice(5)),
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      max: Math.ceil(max * 1.2),
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 28,
        data: points.map((p) => p.count),
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#8b5cf6' },
            { offset: 1, color: '#6366f1' },
          ]),
        },
        emphasis: { itemStyle: { color: '#4f46e5' } },
      },
    ],
  })
}

onMounted(() => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
    render()
  }
})

watch(() => props.data, render, { deep: true })

onBeforeUnmount(() => chart?.dispose())
</script>
