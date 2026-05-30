import {
  ComposedChart, Line, Area, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import type { TrendPoint, MonthlyTotal, CategoryTrend } from '../types'
import { formatCurrency, monthLabel, CATEGORY_COLORS, CATEGORY_ICONS } from '../utils'
import { useState } from 'react'

interface Props {
  trends: TrendPoint[]
  monthlyTotals: MonthlyTotal[]
  categoryTrends: CategoryTrend[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="card px-3 py-2 text-sm shadow-2xl max-w-xs">
      <p className="font-semibold text-white mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="text-xs">
          {p.name}: {formatCurrency(p.value)}
          {p.payload?.is_forecast ? ' (previsão)' : ''}
        </p>
      ))}
    </div>
  )
}

export default function TrendChart({ trends, monthlyTotals, categoryTrends }: Props) {
  const [view, setView] = useState<'overall' | 'category'>('overall')
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(
    new Set(categoryTrends.slice(0, 5).map((ct) => ct.category))
  )

  // Merge real data with trend line for overall view
  const overallData = trends.map((tp) => {
    const key = `${tp.year}-${String(tp.month).padStart(2, '0')}`
    const actual = monthlyTotals.find(
      (m) => m.year === tp.year && m.month === tp.month
    )
    return {
      label: monthLabel(tp.year, tp.month),
      key,
      trend: tp.total,
      actual: actual?.total ?? (tp.is_forecast ? undefined : 0),
      is_forecast: tp.is_forecast,
    }
  })

  // Build category trend data
  const allMonthKeys = trends.map((tp) => ({
    key: `${tp.year}-${String(tp.month).padStart(2, '0')}`,
    label: monthLabel(tp.year, tp.month),
    is_forecast: tp.is_forecast,
  }))

  const categoryData = allMonthKeys.map(({ key, label, is_forecast }) => {
    const point: Record<string, any> = { label, is_forecast }
    for (const ct of categoryTrends) {
      if (selectedCategories.has(ct.category)) {
        const [year, month] = key.split('-').map(Number)
        const tp = ct.points.find((p) => p.year === year && p.month === month)
        point[ct.category] = tp?.total ?? 0
      }
    }
    return point
  })

  const forecastStart = overallData.findIndex((d) => d.is_forecast)
  const forecastLabel =
    forecastStart >= 0 ? overallData[forecastStart]?.label : undefined

  const toggleCategory = (cat: string) => {
    setSelectedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(cat)) next.delete(cat)
      else next.add(cat)
      return next
    })
  }

  return (
    <div className="card p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <h2 className="text-lg font-semibold text-white">Tendências de Gasto</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setView('overall')}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              view === 'overall'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            Geral
          </button>
          <button
            onClick={() => setView('category')}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              view === 'category'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            Por Categoria
          </button>
        </div>
      </div>

      {view === 'overall' ? (
        <>
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={overallData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
              <defs>
                <linearGradient id="actualGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
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
                  <span className="text-gray-300 text-xs capitalize">{value}</span>
                )}
              />
              {forecastLabel && (
                <ReferenceLine
                  x={forecastLabel}
                  stroke="#6b7280"
                  strokeDasharray="4 4"
                  label={{ value: 'Previsão →', fill: '#6b7280', fontSize: 11 }}
                />
              )}
              <Area
                type="monotone"
                dataKey="actual"
                name="Real"
                stroke="#8b5cf6"
                fill="url(#actualGradient)"
                strokeWidth={2}
                dot={{ r: 3, fill: '#8b5cf6' }}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="trend"
                name="Tendência"
                stroke="#f97316"
                strokeWidth={2}
                strokeDasharray="5 3"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>

          <div className="mt-4 p-3 bg-gray-800/50 rounded-xl text-sm text-gray-400">
            <span className="text-orange-400 font-medium">Linha laranja</span>: regressão linear sobre seus gastos históricos projetada para os próximos 3 meses.
            A área roxa mostra os gastos reais mês a mês.
          </div>
        </>
      ) : (
        <>
          {/* Category selector */}
          <div className="flex flex-wrap gap-2 mb-4">
            {categoryTrends.slice(0, 10).map((ct) => (
              <button
                key={ct.category}
                onClick={() => toggleCategory(ct.category)}
                className={`badge border transition-colors ${
                  selectedCategories.has(ct.category)
                    ? 'opacity-100 border-transparent'
                    : 'opacity-40 border-gray-700 bg-gray-800'
                }`}
                style={
                  selectedCategories.has(ct.category)
                    ? {
                        backgroundColor: `${CATEGORY_COLORS[ct.category]}30`,
                        borderColor: CATEGORY_COLORS[ct.category],
                        color: CATEGORY_COLORS[ct.category],
                      }
                    : {}
                }
              >
                {CATEGORY_ICONS[ct.category]} {ct.category}
              </button>
            ))}
          </div>

          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={categoryData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="label"
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v) => `R$${(v / 1000).toFixed(1)}k`}
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                formatter={(value) => (
                  <span style={{ color: CATEGORY_COLORS[value] }} className="text-xs">
                    {CATEGORY_ICONS[value]} {value}
                  </span>
                )}
              />
              {forecastLabel && (
                <ReferenceLine
                  x={forecastLabel}
                  stroke="#6b7280"
                  strokeDasharray="4 4"
                />
              )}
              {Array.from(selectedCategories).map((cat) => (
                <Line
                  key={cat}
                  type="monotone"
                  dataKey={cat}
                  name={cat}
                  stroke={CATEGORY_COLORS[cat] ?? '#6b7280'}
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls
                />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  )
}
