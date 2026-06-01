import { useRef, useState } from 'react'
import axios from 'axios'
import { BANK_LABELS } from '../utils'

interface FileResult {
  filename: string
  bank: string | null
  transactions_found: number
  transactions_imported: number
  error?: string
}

interface UploadResponse {
  success: boolean
  files: FileResult[]
  total_imported: number
  message: string
}

interface Props {
  onImportDone: () => void
}

const BANK_COLORS: Record<string, string> = {
  nubank: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  itau: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  santander: 'bg-red-500/20 text-red-300 border-red-500/30',
}

function detectBankFromName(filename: string): string | null {
  const name = filename.toLowerCase()
  if (/itau|ita[uú]/.test(name)) return 'itau'
  if (/santander/.test(name)) return 'santander'
  if (/nubank/.test(name)) return 'nubank'
  return null
}

export default function FileUploader({ onImportDone }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)

  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [dragging, setDragging] = useState(false)

  const addFiles = (newFiles: FileList | null) => {
    if (!newFiles) return
    const pdfs = Array.from(newFiles).filter((f) =>
      f.name.toLowerCase().endsWith('.pdf')
    )
    setSelectedFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.name))
      const unique = pdfs.filter((f) => !existingNames.has(f.name))
      return [...prev, ...unique]
    })
    setResult(null)
  }

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
    setResult(null)
  }

  const clearAll = () => {
    setSelectedFiles([])
    setResult(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    if (folderInputRef.current) folderInputRef.current.value = ''
  }

  const handleUpload = async () => {
    if (!selectedFiles.length) return

    setUploading(true)
    setProgress(0)
    setResult(null)

    const formData = new FormData()
    selectedFiles.forEach((f) => formData.append('files', f))

    try {
      const res = await axios.post<UploadResponse>('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 100))
        },
        withCredentials: true,
      })
      setResult(res.data)
      if (res.data.total_imported > 0) onImportDone()
    } catch (e: any) {
      setResult({
        success: false,
        files: [],
        total_imported: 0,
        message: e?.response?.data?.detail ?? 'Erro ao enviar os arquivos',
      })
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(e.dataTransfer.files)
  }

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-white mb-1">Importar Faturas</h2>
      <p className="text-sm text-gray-400 mb-5">
        Selecione os PDFs das faturas do Nubank, Itaú e Santander
      </p>

      {/* Dropzone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors mb-4 ${
          dragging
            ? 'border-purple-500 bg-purple-500/10'
            : 'border-gray-700 hover:border-gray-600'
        }`}
      >
        <div className="text-4xl mb-3">📄</div>
        <p className="text-gray-300 text-sm mb-4">
          Arraste os PDFs aqui ou use os botões abaixo
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {/* File picker */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="btn-secondary flex items-center gap-2 text-sm"
          >
            <span>📂</span> Selecionar Arquivos
          </button>

          {/* Folder picker */}
          <input
            ref={folderInputRef}
            type="file"
            accept=".pdf"
            multiple
            // @ts-ignore — non-standard but widely supported
            webkitdirectory=""
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />
          <button
            onClick={() => folderInputRef.current?.click()}
            className="btn-secondary flex items-center gap-2 text-sm"
          >
            <span>🗂️</span> Selecionar Pasta
          </button>
        </div>
      </div>

      {/* File list */}
      {selectedFiles.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">
              {selectedFiles.length} arquivo{selectedFiles.length !== 1 ? 's' : ''} selecionado{selectedFiles.length !== 1 ? 's' : ''}
            </span>
            <button onClick={clearAll} className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
              Limpar tudo
            </button>
          </div>

          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
            {selectedFiles.map((file, i) => {
              const bank = detectBankFromName(file.name)
              const fileResult = result?.files.find((r) => r.filename === file.name)
              return (
                <div
                  key={i}
                  className="flex items-center gap-3 bg-gray-800/60 rounded-lg px-3 py-2 text-sm"
                >
                  <span className="text-gray-400 flex-shrink-0">📄</span>
                  <span className="flex-1 text-gray-200 truncate" title={file.name}>
                    {file.name}
                  </span>

                  {/* Bank badge */}
                  {bank && (
                    <span className={`badge border flex-shrink-0 ${BANK_COLORS[bank] ?? ''}`}>
                      {BANK_LABELS[bank]}
                    </span>
                  )}
                  {!bank && (
                    <span className="badge border border-gray-600 bg-gray-800 text-gray-400 flex-shrink-0">
                      Detectar
                    </span>
                  )}

                  {/* Result badge */}
                  {fileResult && (
                    fileResult.error ? (
                      <span className="text-xs text-red-400 flex-shrink-0" title={fileResult.error}>
                        ✗ Erro
                      </span>
                    ) : (
                      <span className="text-xs text-green-400 flex-shrink-0">
                        ✓ {fileResult.transactions_imported} tx
                      </span>
                    )
                  )}

                  {/* Remove */}
                  {!uploading && !result && (
                    <button
                      onClick={() => removeFile(i)}
                      className="text-gray-600 hover:text-gray-300 flex-shrink-0 transition-colors"
                    >
                      ✕
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Upload progress */}
      {uploading && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Enviando e processando...</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Result summary */}
      {result && (
        <div className={`mb-4 p-3 rounded-xl text-sm ${
          result.total_imported > 0
            ? 'bg-green-500/10 border border-green-500/30 text-green-400'
            : result.success
            ? 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-400'
            : 'bg-red-500/10 border border-red-500/30 text-red-400'
        }`}>
          <p className="font-medium mb-1">{result.message}</p>
          {result.files.some((f) => f.error) && (
            <ul className="text-xs space-y-0.5 mt-1">
              {result.files.filter((f) => f.error).map((f, i) => (
                <li key={i}>⚠ {f.filename}: {f.error}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Upload button */}
      {selectedFiles.length > 0 && !result && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {uploading ? (
            <>
              <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
              Processando...
            </>
          ) : (
            <>
              ↑ Importar {selectedFiles.length} arquivo{selectedFiles.length !== 1 ? 's' : ''}
            </>
          )}
        </button>
      )}

      {/* Upload more after success */}
      {result && selectedFiles.length > 0 && (
        <button onClick={clearAll} className="btn-secondary w-full text-sm">
          + Importar mais arquivos
        </button>
      )}
    </div>
  )
}
