cat > /workspaces/flexiread2/frontend/src/App.tsx << 'EOF'
import { useState, useCallback } from 'react'
import ReaderView from './components/ReaderView'
import './App.css'

function App() {
  const [progress, setProgress] = useState({ pageNumber: 1, blockIndex: 0 })
  const [bookId, setBookId] = useState<string | null>(null)
  const [bookContent, setBookContent] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleProgressChange = useCallback((pageNumber: number, blockIndex: number) => {
    setProgress({ pageNumber, blockIndex })
  }, [])

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setLoading(true)
    setError(null)

    try {
      // 1. Login to get token
      const loginRes = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'demo@flexiread.com', password: 'demo12345' })
      })
      const loginData = await loginRes.json()
      const token = loginData.access_token

      // 2. Get upload URL
      const uploadUrlRes = await fetch('http://localhost:8000/api/v1/books/upload-url', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filename: file.name, content_type: file.type })
      })
      const uploadData = await uploadUrlRes.json()

      // 3. Upload PDF
      await fetch(uploadData.upload_url, {
        method: 'PUT',
        headers: { 'Content-Type': file.type },
        body: file
      })

      // 4. Set book ID and content
      setBookId(uploadData.book_id)
      
      // Poll for status
      const checkStatus = async () => {
        const statusRes = await fetch(`http://localhost:8000/api/v1/books/${uploadData.book_id}/status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const statusData = await statusRes.json()
        
        if (statusData.status === 'completed') {
          const contentRes = await fetch(`http://localhost:8000/api/v1/books/${uploadData.book_id}/content`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          const contentData = await contentRes.json()
          setBookContent(contentData)
          setLoading(false)
        } else if (statusData.status === 'failed') {
          setError('OCR failed')
          setLoading(false)
        } else {
          setTimeout(checkStatus, 2000) // Check again in 2 seconds
        }
      }
      
      checkStatus()
      
    } catch (err) {
      setError('Upload failed: ' + (err as Error).message)
      setLoading(false)
    }
  }

  return (
    <div className="App">
      {!bookId && (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <h1>FlexiRead</h1>
          <p>Upload a PDF to start reading</p>
          <input 
            type="file" 
            accept=".pdf" 
            onChange={handleFileUpload}
            disabled={loading}
          />
          {loading && <p>Uploading and processing...</p>}
          {error && <p style={{ color: 'red' }}>{error}</p>}
        </div>
      )}
      
      {bookId && bookContent && (
        <>
          <ReaderView
            bookId={bookId}
            bookContent={bookContent}
            onProgressChange={handleProgressChange}
          />
          <div style={{ position: 'fixed', bottom: 0, left: 0, background: 'rgba(0,0,0,0.7)', color: 'white', padding: '5px 10px', fontSize: '0.8em' }}>
            Progress: Page {progress.pageNumber}, Block {progress.blockIndex}
          </div>
        </>
      )}
    </div>
  )
}

export default App
EOF
