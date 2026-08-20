export type Bank = 'nubank' | 'itau' | 'santander'

export type Category =
  | 'Alimentação'
  | 'Mercado'
  | 'Transporte'
  | 'Saúde'
  | 'Educação'
  | 'Entretenimento'
  | 'Vestuário'
  | 'Farmácia'
  | 'Viagem'
  | 'Serviços'
  | 'Casa'
  | 'Tecnologia'
  | 'Outros'

export interface Transaction {
  id: number
  external_id: string
  bank: Bank
  description: string
  amount: number
  transaction_date: string
  category: Category
  invoice_month: number
  invoice_year: number
}

export interface CategoryTotal {
  category: string
  total: number
  count: number
  percentage: number
}

export interface MonthlyTotal {
  year: number
  month: number
  total: number
  by_bank: Record<string, number>
  by_category: Record<string, number>
}

export interface TrendPoint {
  year: number
  month: number
  total: number
  is_forecast: boolean
}

export interface CategoryTrend {
  category: string
  points: TrendPoint[]
}

export interface DashboardData {
  total_period: number
  months_analyzed: number
  transactions_count: number
  categories: CategoryTotal[]
  monthly_totals: MonthlyTotal[]
  trends: TrendPoint[]
  category_trends: CategoryTrend[]
  by_bank: Record<string, number>
  last_sync: string | null
}

export interface AuthStatus {
  authenticated: boolean
  email?: string
}

export interface WaterReading {
  reading_date: string
  consumo_m3: number
}

export interface WaterTierBreakdown {
  ate_m3: number | null
  m3_na_faixa: number
  tarifa_agua_m3: number
  tarifa_esgoto_m3: number
  valor_agua: number
  valor_esgoto: number
}

export interface WaterBill {
  consumo_m3: number
  valor_agua: number
  valor_esgoto: number
  taxa_fixa: number
  valor_total: number
  faixas: WaterTierBreakdown[]
  configurado: boolean
  categoria: string
}

export interface WaterMonthlyTotal {
  year: number
  month: number
  consumo_m3: number
}

export interface WaterDashboardData {
  readings: WaterReading[]
  monthly_totals: WaterMonthlyTotal[]
  consumo_periodo_m3: number
  media_diaria_m3: number
  bill: WaterBill
  last_sync: string | null
}
