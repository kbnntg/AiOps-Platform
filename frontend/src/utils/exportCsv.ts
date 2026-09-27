/**
 * 纯前端 CSV 导出工具（不需要后端配合）
 */

export interface CsvColumn<T = any> {
  /** 列标题（导出文件表头） */
  label: string
  /** 取值函数 */
  value: (row: T) => unknown
}

function escapeCell(input: unknown): string {
  if (input === null || input === undefined) return ''
  const text = String(input)
  // 含逗号 / 引号 / 换行时按 RFC4180 加引号转义
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

/** 生成 YYYYMMDD-HHmmss 形式的时间戳，用于文件名 */
export function fileTimestamp(date = new Date()): string {
  const pad = (n: number) => (n < 10 ? `0${n}` : String(n))
  return (
    `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}-` +
    `${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
  )
}

/**
 * 导出 CSV 并触发浏览器下载
 * @param filename 文件名（不含扩展名）
 * @param columns  列定义
 * @param rows     数据行
 */
export function exportCsv<T>(filename: string, columns: CsvColumn<T>[], rows: T[]): void {
  const header = columns.map((c) => escapeCell(c.label)).join(',')
  const body = rows
    .map((row) => columns.map((c) => escapeCell(c.value(row))).join(','))
    .join('\r\n')
  // \uFEFF = BOM，让 Excel 正确识别 UTF-8 中文
  const csv = `\uFEFF${header}\r\n${body}`

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}-${fileTimestamp()}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
