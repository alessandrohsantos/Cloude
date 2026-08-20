import type { WaterBill } from '../../types'
import { formatCurrency } from '../../utils'

interface Props {
  bill: WaterBill
}

export default function WaterBillBreakdown({ bill }: Props) {
  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-white mb-4">
        Cálculo por Faixa Tarifária
      </h2>

      {!bill.configurado && (
        <div className="mb-4 p-3 rounded-xl text-sm bg-amber-500/10 border border-amber-500/30 text-amber-400">
          ⚠️ As tarifas ainda não foram configuradas — os valores abaixo são zero.
          Edite <code className="bg-gray-800 px-1.5 py-0.5 rounded text-gray-300">
            backend/app/water/sabesp_tarifas.json
          </code> com os valores de R$/m³ atuais da Sabesp (ou da sua conta de água) e marque{' '}
          <code className="bg-gray-800 px-1.5 py-0.5 rounded text-gray-300">"configurado": true</code>.
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 text-xs uppercase tracking-wider border-b border-gray-800">
              <th className="pb-2 pr-4">Faixa</th>
              <th className="pb-2 pr-4">m³ na faixa</th>
              <th className="pb-2 pr-4">Tarifa água</th>
              <th className="pb-2 pr-4">Tarifa esgoto</th>
              <th className="pb-2">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {bill.faixas
              .filter((f) => f.m3_na_faixa > 0)
              .map((f, i) => (
                <tr key={i} className="border-b border-gray-800/50">
                  <td className="py-2 pr-4 text-gray-300">
                    até {f.ate_m3 ?? '∞'} m³
                  </td>
                  <td className="py-2 pr-4 text-white">
                    {f.m3_na_faixa.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} m³
                  </td>
                  <td className="py-2 pr-4 text-gray-400">
                    {formatCurrency(f.tarifa_agua_m3)}/m³
                  </td>
                  <td className="py-2 pr-4 text-gray-400">
                    {formatCurrency(f.tarifa_esgoto_m3)}/m³
                  </td>
                  <td className="py-2 text-white font-medium">
                    {formatCurrency(f.valor_agua + f.valor_esgoto)}
                  </td>
                </tr>
              ))}
            {bill.faixas.every((f) => f.m3_na_faixa === 0) && (
              <tr>
                <td colSpan={5} className="py-4 text-center text-gray-500">
                  Sem consumo registrado no mês atual.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-800 space-y-1 text-sm">
        <div className="flex justify-between text-gray-400">
          <span>Total água</span>
          <span>{formatCurrency(bill.valor_agua)}</span>
        </div>
        <div className="flex justify-between text-gray-400">
          <span>Total esgoto</span>
          <span>{formatCurrency(bill.valor_esgoto)}</span>
        </div>
        {bill.taxa_fixa > 0 && (
          <div className="flex justify-between text-gray-400">
            <span>Taxa fixa</span>
            <span>{formatCurrency(bill.taxa_fixa)}</span>
          </div>
        )}
        <div className="flex justify-between text-white font-semibold text-base pt-1">
          <span>Total estimado</span>
          <span>{formatCurrency(bill.valor_total)}</span>
        </div>
      </div>
    </div>
  )
}
