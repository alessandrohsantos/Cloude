import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export function formatCurrency(value: number): string {
  return value.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  })
}

export function formatDate(isoString: string): string {
  try {
    return format(parseISO(isoString), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })
  } catch {
    return isoString
  }
}

export function formatDateOnly(isoDate: string): string {
  try {
    return format(parseISO(isoDate), 'dd/MM/yyyy', { locale: ptBR })
  } catch {
    return isoDate
  }
}

export function monthLabel(year: number, month: number): string {
  const months = [
    'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
  ]
  return `${months[month - 1]}/${String(year).slice(2)}`
}

export const CATEGORY_COLORS: Record<string, string> = {
  Alimentação: '#f97316',
  Mercado: '#22c55e',
  Transporte: '#3b82f6',
  Saúde: '#ec4899',
  Educação: '#8b5cf6',
  Entretenimento: '#eab308',
  Vestuário: '#14b8a6',
  Farmácia: '#ef4444',
  Viagem: '#06b6d4',
  Serviços: '#a855f7',
  Casa: '#84cc16',
  Tecnologia: '#6366f1',
  Outros: '#6b7280',
}

export const BANK_COLORS: Record<string, string> = {
  nubank: '#820AD1',
  itau: '#EC7000',
  santander: '#CC0000',
}

export const BANK_LABELS: Record<string, string> = {
  nubank: 'Nubank',
  itau: 'Itaú',
  santander: 'Santander',
}

export const CATEGORY_ICONS: Record<string, string> = {
  Alimentação: '🍽️',
  Mercado: '🛒',
  Transporte: '🚗',
  Saúde: '💊',
  Educação: '📚',
  Entretenimento: '🎬',
  Vestuário: '👕',
  Farmácia: '💉',
  Viagem: '✈️',
  Serviços: '⚙️',
  Casa: '🏠',
  Tecnologia: '💻',
  Outros: '📦',
}
