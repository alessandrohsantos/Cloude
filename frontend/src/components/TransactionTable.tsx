import { useState, useEffect } from 'react'
import type { Transaction, Category } from '../types'
import { formatCurrency, CATEGORY_COLORS, CATEGORY_ICONS, BANK_LABELS } from '../utils'
import { getTransactions, updateTransactionCategory } from '../api/client'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const ALL_CATEGORIES: Category[] = [
  'Alimentação', 'Mercado', 'Transporte', 'Saúde', 'Educação',
  'Entretenimento', 'Vestuário', 'Farmácia', 'Viagem', 'Serviços',
  'Casa', 'Tecnologia', 'Outros',
]

const BANK_BADGE: Record<string, string> = {
  nubank: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  itau: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  santander: 'bg-red-500/20 text-red-300 border-red-500/30',
}

interface Props {
  months: number
}

export default function TransactionTable({ months }: Props) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterBank, setFilterBank] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  useEffect(() => {
    setLoading(true)
    getTransactions(months, filterBank || undefined, filterCategory || undefined)
      .then(setTransactions)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [months, filterBank, filterCategory])

  const filtered = transactions.filter((tx) =>
    tx.description.toLowerCase().includes(search.toLowerCase())
  )

  const paginated = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)

  const handleCategoryChange = async (id: number, category: Category) => {
    try {
      await updateTransactionCategory(id, category)
      setTransactions((prev) =>
        prev.map((tx) => (tx.id === id ? { ...tx, category } : tx))
      )
    } catch {
      alert('Erro ao atualizar categoria')
    }
    setEditingId(null)
  }

  return (
    <div className="card p-6">
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <h2 className="text-lg font-semibold text-white sm:flex-1">
          Transações
          <span className="ml-2 text-sm text-gray-400 font-normal">
            ({filtered.length})
          </span>
        </h2>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <input
          type="text"
          placeholder="Buscar descrição..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0) }}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
        />
        <select
          value={filterBank}
          onChange={(e) => { setFilterBank(e.target.value); setPage(0) }}
          className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-purple-500"
        >
          <option value="">Todos os bancos</option>
          <option value="nubank">Nubank</option>
          <option value="itau">Itaú</option>
          <option value="santander">Santander</option>
        </select>
        <select
          value={filterCategory}
          onChange={(e) => { setFilterCategory(e.target.value); setPage(0) }}
          className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-purple-500"
        >
          <option value="">Todas as categorias</option>
          {ALL_CATEGORIES.map((c) => (
            <option key={c} value={c}>{CATEGORY_ICONS[c]} {c}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
        </div>
      ) : paginated.length === 0 ? (
        <div className="text-center py-10 text-gray-500">
          Nenhuma transação encontrada
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  <th className="pb-3 pr-4 font-medium">Data</th>
                  <th className="pb-3 pr-4 font-medium">Descrição</th>
                  <th className="pb-3 pr-4 font-medium">Banco</th>
                  <th className="pb-3 pr-4 font-medium">Categoria</th>
                  <th className="pb-3 text-right font-medium">Valor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {paginated.map((tx) => (
                  <tr key={tx.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="py-3 pr-4 text-gray-400 whitespace-nowrap">
                      {format(parseISO(tx.transaction_date), 'dd/MM/yy', { locale: ptBR })}
                    </td>
                    <td className="py-3 pr-4 text-gray-200 max-w-xs truncate">
                      {tx.description}
                    </td>
                    <td className="py-3 pr-4">
                      <span className={`badge border ${BANK_BADGE[tx.bank] ?? 'bg-gray-800 text-gray-300 border-gray-700'}`}>
                        {BANK_LABELS[tx.bank] ?? tx.bank}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      {editingId === tx.id ? (
                        <select
                          autoFocus
                          defaultValue={tx.category}
                          onBlur={() => setEditingId(null)}
                          onChange={(e) => handleCategoryChange(tx.id, e.target.value as Category)}
                          className="bg-gray-800 border border-gray-600 rounded-lg px-2 py-1 text-xs text-gray-200 focus:outline-none"
                        >
                          {ALL_CATEGORIES.map((c) => (
                            <option key={c} value={c}>{CATEGORY_ICONS[c]} {c}</option>
                          ))}
                        </select>
                      ) : (
                        <button
                          onClick={() => setEditingId(tx.id)}
                          className="badge border hover:opacity-80 transition-opacity"
                          style={{
                            backgroundColor: `${CATEGORY_COLORS[tx.category]}20`,
                            borderColor: `${CATEGORY_COLORS[tx.category]}40`,
                            color: CATEGORY_COLORS[tx.category],
                          }}
                          title="Clique para editar"
                        >
                          {CATEGORY_ICONS[tx.category]} {tx.category}
                        </button>
                      )}
                    </td>
                    <td className="py-3 text-right font-medium text-white whitespace-nowrap">
                      {formatCurrency(tx.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-4">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn-secondary text-sm disabled:opacity-40"
              >
                ←
              </button>
              <span className="flex items-center text-sm text-gray-400">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="btn-secondary text-sm disabled:opacity-40"
              >
                →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
