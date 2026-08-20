import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { WaterReading } from '../../types'
import { formatDateOnly } from '../../utils'

interface Props {
  readings: WaterReading[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="card px-3 py-2 text-sm shadow-2xl">
      <p className="font-semibold text-white mb-1">{formatDateOnly(label)}</p>
      <p className="text-xs text-cyan-400">
        {payload[0].value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} m³
      </p>
    </div>
  )
}

export default function WaterConsumptionChart({ readings }: Props) {
  const data = readings.map((r) => ({
    date: r.reading_date,
    consumo: r.consumo_m3,
  }))

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-white mb-6">Consumo Diário de Água</h2>
      {data.length === 0 ? (
        <p className="text-sm text-gray-500">Sem leituras no período selecionado.</p>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
            <defs>
              <linearGradient id="waterGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="date"
              tickFormatter={(d) => formatDateOnly(d).slice(0, 5)}
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => `${v}m³`}
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="consumo"
              stroke="#06b6d4"
              strokeWidth={2}
              fill="url(#waterGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
