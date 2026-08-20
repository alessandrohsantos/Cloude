import type { WaterDashboardData } from '../../types'
import { formatCurrency, formatDate } from '../../utils'

interface Props {
  data: WaterDashboardData
}

export default function WaterSummaryCards({ data }: Props) {
  const { bill, media_diaria_m3, consumo_periodo_m3, last_sync } = data

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="card p-5">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
          Consumo do Mês
        </p>
        <p className="text-2xl font-bold text-white">
          {bill.consumo_m3.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} m³
        </p>
        <p className="text-xs text-gray-500 mt-1">
          média de {media_diaria_m3.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} m³/dia
        </p>
      </div>

      <div className="card p-5">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
          Valor Estimado da Conta
        </p>
        <p className="text-2xl font-bold text-white">{formatCurrency(bill.valor_total)}</p>
        <p className="text-xs text-gray-500 mt-1">
          água {formatCurrency(bill.valor_agua)} + esgoto {formatCurrency(bill.valor_esgoto)}
          {bill.taxa_fixa > 0 ? ` + taxa fixa ${formatCurrency(bill.taxa_fixa)}` : ''}
        </p>
      </div>

      <div className="card p-5">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
          Consumo no Período
        </p>
        <p className="text-2xl font-bold text-white">
          {consumo_periodo_m3.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} m³
        </p>
        <p className="text-xs text-gray-500 mt-1">{data.readings.length} leituras</p>
      </div>

      <div className="card p-5">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
          Última Sincronização
        </p>
        <p className="text-sm font-medium text-white">
          {last_sync ? formatDate(last_sync) : 'Nunca sincronizado'}
        </p>
        <p className="text-xs text-gray-500 mt-1">categoria: {bill.categoria || '—'}</p>
      </div>
    </div>
  )
}
