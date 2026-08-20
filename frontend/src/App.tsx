import { useState, useEffect, useCallback } from 'react'
import type { DashboardData, AuthStatus, WaterDashboardData } from './types'
import { getAuthStatus, startGoogleAuth, logout, syncTransactions, getDashboard, getWaterDashboard } from './api/client'
import SummaryCards from './components/SummaryCards'
import CategoryChart from './components/CategoryChart'
import TrendChart from './components/TrendChart'
import MonthlyChart from './components/MonthlyChart'
import TransactionTable from './components/TransactionTable'
import FileUploader from './components/FileUploader'
import WaterDashboard from './components/water/WaterDashboard'

type Tab = 'dashboard' | 'transactions' | 'import' | 'water'

export default function App() {
  const [auth, setAuth] = useState<AuthStatus>({ authenticated: false })
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [waterDashboard, setWaterDashboard] = useState<WaterDashboardData | null>(null)
  const [months, setMonths] = useState(3)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('import')

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
    } catch {
      // auth check failed — continue without auth
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

  const fetchWaterDashboard = useCallback(async (m: number) => {
    try {
      const data = await getWaterDashboard(m)
      setWaterDashboard(data)
    } catch (e) {
      console.error('Water dashboard fetch failed', e)
    }
  }, [])

  useEffect(() => {
    fetchDashboard(months)
    fetchWaterDashboard(months)
  }, [fetchDashboard, fetchWaterDashboard, months])

  const handleLogin = async () => {
    const url = await startGoogleAuth()
    window.location.href = url
  }

  const handleLogout = async () => {
    await logout()
    setAuth({ authenticated: false })
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

  const handleImportDone = () => {
    fetchDashboard(months)
    // Switch to dashboard after import
    setTimeout(() => setActiveTab('dashboard'), 800)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-500" />
      </div>
    )
  }

  const hasData = dashboard && dashboard.transactions_count > 0

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-gray-950/80 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 gap-4">
            {/* Logo */}
            <div className="flex items-center gap-3 flex-shrink-0">
              <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center font-bold text-sm">
                💳
              </div>
              <span className="font-semibold text-white hidden sm:block">Controle de Faturas</span>
            </div>

            {/* Gmail sync (optional) */}
            <div className="flex items-center gap-2 flex-1 justify-end">
              {auth.authenticated ? (
                <>
                  <span className="text-xs text-gray-500 hidden md:block">{auth.email}</span>
                  <button
                    onClick={handleSync}
                    disabled={syncing}
                    className="btn-secondary text-xs flex items-center gap-1.5"
                    title="Sincronizar via Gmail"
                  >
                    {syncing
                      ? <span className="animate-spin inline-block w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full" />
                      : '↻'
                    }
                    <span className="hidden sm:inline">Gmail</span>
                  </button>
                  <button onClick={handleLogout} className="btn-secondary text-xs">
                    Sair
                  </button>
                </>
              ) : (
                <button
                  onClick={handleLogin}
                  className="btn-secondary text-xs flex items-center gap-1.5"
                  title="Conectar Gmail para sincronização automática"
                >
                  <GoogleIcon />
                  <span className="hidden sm:inline">Conectar Gmail</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Sync message */}
        {syncMessage && (
          <div className={`mb-4 p-3 rounded-xl text-sm ${
            syncMessage.includes('Erro')
              ? 'bg-red-500/10 border border-red-500/30 text-red-400'
              : 'bg-green-500/10 border border-green-500/30 text-green-400'
          }`}>
            {syncMessage}
          </div>
        )}

        {/* Period selector + tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
          <div className="flex gap-1 bg-gray-900 rounded-xl p-1 w-fit">
            {(['import', 'dashboard', 'transactions', 'water'] as Tab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  activeTab === tab
                    ? 'bg-gray-700 text-white font-medium'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {tab === 'import' ? '↑ Importar' : tab === 'dashboard' ? 'Dashboard' : tab === 'transactions' ? 'Transações' : '💧 Água'}
              </button>
            ))}
          </div>

          {activeTab !== 'import' && (
            <div className="flex items-center gap-2 sm:ml-auto">
              <span className="text-sm text-gray-400">Período:</span>
              {[1, 3, 6, 12].map((m) => (
                <button
                  key={m}
                  onClick={() => setMonths(m)}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    months === m
                      ? 'bg-purple-600 text-white font-medium'
                      : 'bg-gray-800 text-gray-400 hover:text-white'
                  }`}
                >
                  {m === 1 ? '1 mês' : `${m}m`}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Import tab */}
        {activeTab === 'import' && (
          <div className="max-w-2xl">
            <FileUploader onImportDone={handleImportDone} />
            <div className="mt-4 p-4 bg-gray-900/50 rounded-xl text-xs text-gray-500 space-y-1">
              <p className="font-medium text-gray-400 mb-2">Senhas dos PDFs</p>
              <p>🟠 Itaú: <code className="bg-gray-800 px-1.5 py-0.5 rounded text-gray-300">13970</code> — aplicada automaticamente</p>
              <p>🔴 Santander: <code className="bg-gray-800 px-1.5 py-0.5 rounded text-gray-300">13970639808</code> — aplicada automaticamente</p>
              <p>🟣 Nubank: sem senha</p>
            </div>
          </div>
        )}

        {/* Dashboard tab */}
        {activeTab === 'dashboard' && (
          hasData && dashboard ? (
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
          ) : (
            <EmptyDashboard onGoToImport={() => setActiveTab('import')} />
          )
        )}

        {/* Transactions tab */}
        {activeTab === 'transactions' && (
          hasData ? (
            <TransactionTable months={months} />
          ) : (
            <EmptyDashboard onGoToImport={() => setActiveTab('import')} />
          )
        )}

        {/* Water tab */}
        {activeTab === 'water' && (
          <WaterDashboard data={waterDashboard} onSynced={() => fetchWaterDashboard(months)} />
        )}
      </main>
    </div>
  )
}

function EmptyDashboard({ onGoToImport }: { onGoToImport: () => void }) {
  return (
    <div className="text-center py-16">
      <div className="text-6xl mb-4">📊</div>
      <h3 className="text-xl font-semibold text-white mb-2">Nenhum dado ainda</h3>
      <p className="text-gray-400 mb-6">
        Importe os PDFs das suas faturas para visualizar os gráficos
      </p>
      <button onClick={onGoToImport} className="btn-primary">
        ↑ Importar Faturas
      </button>
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  )
}
