import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import type { CategoryTotal } from '../types'
import { formatCurrency, CATEGORY_COLORS, CATEGORY_ICONS } from '../utils'

interface Props {
  categories: CategoryTotal[]
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const item = payload[0].payload
  return (
    <div className="card px-3 py-2 text-sm shadow-2xl">
      <p className="font-semibold text-white">{CATEGORY_ICONS[item.category] ?? ''} {item.category}</p>
      <p className="text-gray-300">{formatCurrency(item.total)}</p>
      <p className="text-gray-400">{item.count} transações • {item.percentage}%</p>
    </div>
  )
}

export default function CategoryChart({ categories }: Props) {
  if (!categories.length) {
    return (
      <div className="card p-6 text-center text-gray-500">
        Nenhuma categoria disponível
      </div>
    )
  }

  const top10 = categories.slice(0, 10)

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-white mb-6">Gastos por Categoria</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Pie chart */}
        <div>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={top10}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={110}
                paddingAngle={2}
                dataKey="total"
                nameKey="category"
              >
                {top10.map((entry) => (
                  <Cell
                    key={entry.category}
                    fill={CATEGORY_COLORS[entry.category] ?? '#6b7280'}
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                formatter={(value) => (
                  <span className="text-gray-300 text-xs">
                    {CATEGORY_ICONS[value] ?? ''} {value}
                  </span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Bar chart */}
        <div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={top10}
              layout="vertical"
              margin={{ left: 20, right: 30, top: 5, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                type="number"
                tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`}
                tick={{ fill: '#9ca3af', fontSize: 11 }}
              />
              <YAxis
                type="category"
                dataKey="category"
                width={90}
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                tickFormatter={(v) => `${CATEGORY_ICONS[v] ?? ''} ${v}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                {top10.map((entry) => (
                  <Cell
                    key={entry.category}
                    fill={CATEGORY_COLORS[entry.category] ?? '#6b7280'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Category table */}
      <div className="mt-6 space-y-2">
        {categories.map((cat) => (
          <div key={cat.category} className="flex items-center gap-3">
            <span className="text-base w-6 text-center">{CATEGORY_ICONS[cat.category] ?? '📦'}</span>
            <div className="flex-1">
              <div className="flex justify-between text-sm mb-0.5">
                <span className="text-gray-200">{cat.category}</span>
                <span className="text-white font-medium">{formatCurrency(cat.total)}</span>
              </div>
              <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${cat.percentage}%`,
                    backgroundColor: CATEGORY_COLORS[cat.category] ?? '#6b7280',
                  }}
                />
              </div>
            </div>
            <span className="text-xs text-gray-500 w-10 text-right">{cat.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
