export function toMonthStart(date) {
  const d = new Date(date)
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

export function shiftMonth(date, delta) {
  const d = toMonthStart(date)
  d.setMonth(d.getMonth() + delta)
  return d
}

export function isSameMonth(a, b) {
  if (!a || !b) return false
  const da = new Date(a)
  const db = new Date(b)
  return da.getFullYear() === db.getFullYear() && da.getMonth() === db.getMonth()
}

export function formatMonthTitle(date) {
  const d = new Date(date)
  return `${d.getFullYear()}年${d.getMonth() + 1}月`
}

export function getMonthGrid(date) {
  const d = toMonthStart(date)
  const year = d.getFullYear()
  const month = d.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const lastDate = new Date(year, month + 1, 0).getDate()

  const days = []
  for (let i = 0; i < firstDay; i++) {
    days.push('')
  }
  for (let i = 1; i <= lastDate; i++) {
    days.push(i)
  }
  return days
}
