import { useState } from 'react'
import type { WaterDashboardData } from '../../types'
import { syncWater } from '../../api/client'
import WaterSummaryCards from './WaterSummaryCards'
import WaterConsumptionChart from './WaterConsumptionChart'
import WaterBillBreakdown from './WaterBillBreakdown'

interface Props {
  data: WaterDashboardData | null
  onSynced: () => void
}

export default function WaterDashboard({ data, onSynced }: Props) {
  const [syncing, setSyncing] = useState(false)
  const [message, setMessage] = useState('')

  const handleSync = async () => {
    setSyncing(true)
    setMessage('')
    try {
      const result = await syncWater()
      setMessage(result.message)
      onSynced()
    } catch (e: any) {
      setMessage(e?.response?.data?.detail ?? 'Erro sincronizando com o portal Vedrano')
    } finally {
      setSyncing(false)
    }
  }

  const hasData = data && data.readings.length > 0

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <button onClick={handleSync} disabled={syncing} className="btn-primary flex items-center gap-2 w-fit">
          {syncing
            ? <span className="animate-spin inline-block w-4 h-4 border-2 border-white/50 border-t-transparent rounded-full" />
            : '💧'
          }
          {syncing ? 'Sincronizando...' : 'Sincronizar com o Vedrano'}
        </button>
        {message && (
          <span className={`text-sm ${message.toLowerCase().includes('erro') ? 'text-red-400' : 'text-gray-400'}`}>
            {message}
          </span>
        )}
      </div>

      {hasData ? (
        <>
          <WaterSummaryCards data={data} />
          <WaterConsumptionChart readings={data.readings} />
          <WaterBillBreakdown bill={data.bill} />
        </>
      ) : (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">💧</div>
          <h3 className="text-xl font-semibold text-white mb-2">Nenhuma leitura ainda</h3>
          <p className="text-gray-400 mb-2 max-w-md mx-auto">
            Clique em "Sincronizar com o Vedrano" para importar as leituras diárias de
            consumo de água do seu apartamento.
          </p>
          <p className="text-gray-500 text-xs max-w-md mx-auto">
            Requer VEDRANO_LOGIN e VEDRANO_SENHA configurados no .env do backend.
          </p>
        </div>
      )}
    </div>
  )
}
