import type { DashboardData } from '../types'
import { formatCurrency, formatDate } from '../utils'

interface Props {
  data: DashboardData
}

const BANK_COLORS: Record<string, string> = {
  nubank: 'border-purple-500 bg-purple-500/10',
  itau: 'border-orange-500 bg-orange-500/10',
  santander: 'border-red-500 bg-red-500/10',
}

const BANK_LABELS: Record<string, string> = {
  nubank: 'Nubank',
  itau: 'Itaú',
  santander: 'Santander',
}

export default function SummaryCards({ data }: Props) {
  const monthlyAvg =
    data.months_analyzed > 0
      ? data.total_period / data.months_analyzed
      : 0

  // Next month forecast from trends
  const futureTrends = data.trends.filter((p) => p.is_forecast)
  const nextMonthForecast = futureTrends[0]?.total ?? 0

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total Period */}
      <div className="card p-5">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
          Total no Período
        </p>
        <p className="text-2xl font-bold text-white">
          {formatCurrency(data.total_period)}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {data.months_analyzed} {data.months_analyzed === 1 ? 'mês' : 'meses'} •{' '}
          {data.transactions_count} transações
        </p>
      </div>

      {/* Monthly Average */}
      <div className="card p-5">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
          Média Mensal
        </p>
        <p className="text-2xl font-bold text-white">{formatCurrency(monthlyAvg)}</p>
        <p className="text-xs text-gray-500 mt-1">
          média dos últimos {data.months_analyzed} meses
        </p>
      </div>

      {/* Forecast */}
      <div className="card p-5">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
          Previsão Próximo Mês
        </p>
        <p
          className={`text-2xl font-bold ${
            nextMonthForecast > monthlyAvg ? 'text-red-400' : 'text-green-400'
          }`}
        >
          {formatCurrency(nextMonthForecast)}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {nextMonthForecast > monthlyAvg
            ? `↑ ${formatCurrency(nextMonthForecast - monthlyAvg)} acima da média`
            : `↓ ${formatCurrency(monthlyAvg - nextMonthForecast)} abaixo da média`}
        </p>
      </div>

      {/* Last Sync */}
      <div className="card p-5">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
          Última Sincronização
        </p>
        <p className="text-sm font-medium text-white">
          {data.last_sync ? formatDate(data.last_sync) : 'Nunca sincronizado'}
        </p>
        <div className="flex gap-2 mt-2 flex-wrap">
          {Object.entries(data.by_bank).map(([bank, total]) => (
            <span
              key={bank}
              className={`badge border ${BANK_COLORS[bank] ?? 'border-gray-600 bg-gray-800'}`}
            >
              {BANK_LABELS[bank] ?? bank}: {formatCurrency(total)}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
