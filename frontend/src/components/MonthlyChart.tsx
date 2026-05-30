import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, Cell,
} from 'recharts'
import type { MonthlyTotal } from '../types'
import { formatCurrency, monthLabel, BANK_COLORS, BANK_LABELS } from '../utils'

interface Props {
  monthlyTotals: MonthlyTotal[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  const total = payload.reduce((s: number, p: any) => s + (p.value ?? 0), 0)
  return (
    <div className="card px-3 py-2 text-sm shadow-2xl">
      <p className="font-semibold text-white mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.fill }} className="text-xs">
          {BANK_LABELS[p.name] ?? p.name}: {formatCurrency(p.value)}
        </p>
      ))}
      <p className="text-gray-300 text-xs mt-1 border-t border-gray-700 pt-1">
        Total: {formatCurrency(total)}
      </p>
    </div>
  )
}

export default function MonthlyChart({ monthlyTotals }: Props) {
  const data = monthlyTotals.map((m) => ({
    label: monthLabel(m.year, m.month),
    ...m.by_bank,
    _total: m.total,
  }))

  const banks = Array.from(
    new Set(monthlyTotals.flatMap((m) => Object.keys(m.by_bank)))
  )

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-white mb-6">Gastos Mensais por Banco</h2>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="label"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => (
              <span className="text-gray-300 text-xs">{BANK_LABELS[value] ?? value}</span>
            )}
          />
          {banks.map((bank) => (
            <Bar
              key={bank}
              dataKey={bank}
              stackId="a"
              fill={BANK_COLORS[bank] ?? '#6b7280'}
              radius={
                bank === banks[banks.length - 1] ? [4, 4, 0, 0] : [0, 0, 0, 0]
              }
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
