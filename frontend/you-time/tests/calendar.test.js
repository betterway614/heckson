import test from 'node:test'
import assert from 'node:assert/strict'
import { getMonthGrid, shiftMonth, isSameMonth, toMonthStart } from '../src/utils/calendar.js'

test('toMonthStart returns first day of month', () => {
  const d = toMonthStart(new Date(2026, 4, 17, 12, 0, 0))
  assert.equal(d.getFullYear(), 2026)
  assert.equal(d.getMonth(), 4)
  assert.equal(d.getDate(), 1)
})

test('shiftMonth moves to target month start', () => {
  const next = shiftMonth(new Date(2026, 0, 15, 12, 0, 0), 1)
  assert.equal(next.getFullYear(), 2026)
  assert.equal(next.getMonth(), 1)
  assert.equal(next.getDate(), 1)

  const prev = shiftMonth(new Date(2026, 0, 15, 12, 0, 0), -1)
  assert.equal(prev.getFullYear(), 2025)
  assert.equal(prev.getMonth(), 11)
  assert.equal(prev.getDate(), 1)
})

test('isSameMonth matches month and year', () => {
  assert.equal(isSameMonth(new Date('2026-05-01'), new Date('2026-05-31')), true)
  assert.equal(isSameMonth(new Date('2026-05-01'), new Date('2026-06-01')), false)
  assert.equal(isSameMonth(new Date('2025-05-01'), new Date('2026-05-01')), false)
})

test('getMonthGrid includes correct days for leap-year February', () => {
  const grid = getMonthGrid(new Date('2024-02-20'))
  const days = grid.filter(d => d !== '')
  assert.equal(days.length, 29)
  assert.equal(days[0], 1)
  assert.equal(days[days.length - 1], 29)
})
