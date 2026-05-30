import { useState, useEffect, useCallback } from 'react'
import type { DashboardData, AuthStatus } from './types'
import { getAuthStatus, startGoogleAuth, logout, syncTransactions, getDashboard } from './api/client'
import SummaryCards from './components/SummaryCards'
import CategoryChart from './components/CategoryChart'
import TrendChart from './components/TrendChart'
import MonthlyChart from './components/MonthlyChart'
import TransactionTable from './components/TransactionTable'

const BANK_LOGOS: Record<string, { color: string; label: string; initial: string }> = {
  nubank: { color: '#820AD1', label: 'Nubank', initial: 'N' },
  itau: { color: '#EC7000', label: 'Itaú', initial: 'I' },
  santander: { color: '#CC0000', label: 'Santander', initial: 'S' },
}

export default function App() {
  const [auth, setAuth] = useState<AuthStatus>({ authenticated: false })
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [months, setMonths] = useState(3)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')
  const [activeTab, setActiveTab] = useState<'dashboard' | 'transactions'>('dashboard')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('error')) {
      setSyncMessage(`Erro de autenticação: ${params.get('error')}`)
      window.history.replaceState({}, '', '/')
    }
    checkAuth()
  }, [])

  const checkAuth = async () => {
    setLoading(true)
    try {
      const status = await getAuthStatus()
      setAuth(status)
      if (status.authenticated) {
        await fetchDashboard(months)
      }
    } catch (e) {
      console.error('Auth check failed', e)
    } finally {
      setLoading(false)
    }
  }

  const fetchDashboard = useCallback(async (m: number) => {
    try {
      const data = await getDashboard(m)
      setDashboard(data)
    } catch (e) {
      console.error('Dashboard fetch failed', e)
    }
  }, [])

  const handleMonthChange = (m: number) => {
    setMonths(m)
    fetchDashboard(m)
  }

  const handleLogin = async () => {
    const url = await startGoogleAuth()
    window.location.href = url
  }

  const handleLogout = async () => {
    await logout()
    setAuth({ authenticated: false })
    setDashboard(null)
  }

  const handleSync = async () => {
    setSyncing(true)
    setSyncMessage('')
    try {
      const result = await syncTransactions(months)
      setSyncMessage(result.message)
      await fetchDashboard(months)
    } catch (e: any) {
      setSyncMessage(e?.response?.data?.detail ?? 'Erro na sincronização')
    } finally {
      setSyncing(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-500" />
      </div>
    )
  }

  if (!auth.authenticated) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-gray-950/80 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                💳
              </div>
              <span className="font-semibold text-white">Controle de Faturas</span>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400 hidden sm:block">{auth.email}</span>
              <button onClick={handleLogout} className="btn-secondary text-sm">
                Sair
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Controls bar */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">Período:</span>
            {[1, 3, 6, 12].map((m) => (
              <button
                key={m}
                onClick={() => handleMonthChange(m)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  months === m
                    ? 'bg-purple-600 text-white font-medium'
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                {m === 1 ? '1 mês' : `${m} meses`}
              </button>
            ))}
          </div>

          <div className="sm:ml-auto flex items-center gap-3">
            <button
              onClick={handleSync}
              disabled={syncing}
              className="btn-primary flex items-center gap-2"
            >
              {syncing ? (
                <>
                  <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  Sincronizando...
                </>
              ) : (
                <>
                  <span>↻</span> Sincronizar Gmail
                </>
              )}
            </button>
          </div>
        </div>

        {syncMessage && (
          <div className={`mb-4 p-3 rounded-xl text-sm ${
            syncMessage.includes('Erro')
              ? 'bg-red-500/10 border border-red-500/30 text-red-400'
              : 'bg-green-500/10 border border-green-500/30 text-green-400'
          }`}>
            {syncMessage}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-gray-900 rounded-xl p-1 w-fit">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-4 py-2 text-sm rounded-lg transition-colors ${
              activeTab === 'dashboard'
                ? 'bg-gray-700 text-white font-medium'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('transactions')}
            className={`px-4 py-2 text-sm rounded-lg transition-colors ${
              activeTab === 'transactions'
                ? 'bg-gray-700 text-white font-medium'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Transações
          </button>
        </div>

        {activeTab === 'dashboard' && dashboard && (
          <div className="space-y-6">
            <SummaryCards data={dashboard} />

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <CategoryChart categories={dashboard.categories} />
              <MonthlyChart monthlyTotals={dashboard.monthly_totals} />
            </div>

            <TrendChart
              trends={dashboard.trends}
              monthlyTotals={dashboard.monthly_totals}
              categoryTrends={dashboard.category_trends}
            />
          </div>
        )}

        {activeTab === 'dashboard' && !dashboard && (
          <EmptyState onSync={handleSync} syncing={syncing} />
        )}

        {activeTab === 'transactions' && auth.authenticated && (
          <TransactionTable months={months} />
        )}
      </main>
    </div>
  )
}

function LoginPage({ onLogin }: { onLogin: () => void }) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center text-4xl mx-auto mb-4 shadow-xl">
            💳
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Controle de Faturas</h1>
          <p className="text-gray-400">
            Consolide suas faturas do Nubank, Itaú e Santander em um só lugar
          </p>
        </div>

        <div className="card p-6 mb-4">
          <div className="flex justify-center gap-4 mb-6">
            {Object.entries(BANK_LOGOS).map(([key, { color, label, initial }]) => (
              <div key={key} className="flex flex-col items-center gap-2">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-lg"
                  style={{ backgroundColor: color }}
                >
                  {initial}
                </div>
                <span className="text-xs text-gray-400">{label}</span>
              </div>
            ))}
          </div>

          <ul className="space-y-2 text-sm text-gray-400 mb-6">
            <li className="flex items-center gap-2">
              <span className="text-green-400">✓</span> Lê faturas diretamente do Gmail
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-400">✓</span> Categoriza gastos automaticamente
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-400">✓</span> Projeção de tendências futuras
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-400">✓</span> Acesso somente leitura ao Gmail
            </li>
          </ul>

          <button
            onClick={onLogin}
            className="w-full btn-primary flex items-center justify-center gap-3 py-3"
          >
            <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Conectar com Google
          </button>
        </div>

        <p className="text-center text-xs text-gray-600">
          Apenas permissão de leitura. Seus dados ficam no seu dispositivo.
        </p>
      </div>
    </div>
  )
}

function EmptyState({ onSync, syncing }: { onSync: () => void; syncing: boolean }) {
  return (
    <div className="text-center py-16">
      <div className="text-6xl mb-4">📊</div>
      <h3 className="text-xl font-semibold text-white mb-2">Nenhum dado ainda</h3>
      <p className="text-gray-400 mb-6">
        Clique em "Sincronizar Gmail" para buscar suas faturas
      </p>
      <button onClick={onSync} disabled={syncing} className="btn-primary">
        {syncing ? 'Sincronizando...' : '↻ Sincronizar Agora'}
      </button>
    </div>
  )
}
