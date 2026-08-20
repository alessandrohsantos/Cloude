import axios from 'axios'
import type { AuthStatus, DashboardData, Transaction, Category, WaterDashboardData } from '../types'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

export async function getAuthStatus(): Promise<AuthStatus> {
  const res = await api.get('/auth/status')
  return res.data
}

export async function startGoogleAuth(): Promise<string> {
  const res = await api.get('/auth/google')
  return res.data.auth_url
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

export async function syncTransactions(months: number): Promise<{
  success: boolean
  transactions_imported: number
  message: string
}> {
  const res = await api.post('/sync', { months })
  return res.data
}

export async function getDashboard(months: number): Promise<DashboardData> {
  const res = await api.get('/dashboard', { params: { months } })
  return res.data
}

export async function getTransactions(
  months: number,
  bank?: string,
  category?: string
): Promise<Transaction[]> {
  const res = await api.get('/transactions', {
    params: { months, bank, category },
  })
  return res.data
}

export async function updateTransactionCategory(
  id: number,
  category: Category
): Promise<void> {
  await api.put(`/transactions/${id}/category`, null, {
    params: { category },
  })
}

export async function syncWater(): Promise<{
  success: boolean
  readings_imported: number
  message: string
}> {
  const res = await api.post('/water/sync')
  return res.data
}

export async function getWaterDashboard(months: number): Promise<WaterDashboardData> {
  const res = await api.get('/water/dashboard', { params: { months } })
  return res.data
}
