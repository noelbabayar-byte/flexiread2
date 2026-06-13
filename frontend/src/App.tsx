import React, { useCallback, useEffect, useState } from 'react';
import { ReaderView } from './components/ReaderView';
import { BookContent } from './reader/types';
import {
  ApiError,
  BookStatus,
  getBookContent,
  listBooks,
  login,
  logout,
  pollUntilDone,
  register,
  tokenStore,
  uploadAndProcess,
} from './api/client';

type View = 'auth' | 'library' | 'reading';

const panel: React.CSSProperties = {
  maxWidth: 520,
  margin: '60px auto',
  padding: 24,
  fontFamily: 'system-ui, sans-serif',
};

const input: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  margin: '6px 0',
  border: '1px solid #ccc',
  borderRadius: 6,
  boxSizing: 'border-box',
};

const button: React.CSSProperties = {
  padding: '10px 16px',
  border: 'none',
  borderRadius: 6,
  background: '#2563eb',
  color: 'white',
  cursor: 'pointer',
  fontSize: '0.95em',
};

// ---------------------------------------------------------------------------
// Auth screen
// ---------------------------------------------------------------------------

function AuthScreen({ onAuthed }: { onAuthed: () => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === 'register') {
        await register(email, password, fullName || undefined);
      }
      await login(email, password);
      onAuthed();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Bir hata oluştu');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={panel}>
      <h1 style={{ fontSize: '1.6em' }}>FlexiRead</h1>
      <p style={{ color: '#666' }}>
        {mode === 'login' ? 'Giriş yap' : 'Yeni hesap oluştur'}
      </p>
      <form onSubmit={submit}>
        {mode === 'register' && (
          <input
            style={input}
            placeholder="Ad soyad (opsiyonel)"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        )}
        <input
          style={input}
          type="email"
          placeholder="E-posta"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          style={input}
          type="password"
          placeholder="Parola (en az 8 karakter)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
        {error && <p style={{ color: '#dc2626' }}>{error}</p>}
        <button style={{ ...button, width: '100%' }} disabled={busy}>
          {busy ? 'Lütfen bekleyin...' : mode === 'login' ? 'Giriş' : 'Kayıt ol'}
        </button>
      </form>
      <p style={{ marginTop: 16, fontSize: '0.9em' }}>
        {mode === 'login' ? 'Hesabın yok mu? ' : 'Zaten hesabın var mı? '}
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setError(null);
            setMode(mode === 'login' ? 'register' : 'login');
          }}
        >
          {mode === 'login' ? 'Kayıt ol' : 'Giriş yap'}
        </a>
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Library / upload screen
// ---------------------------------------------------------------------------

function LibraryScreen({
  onOpen,
  onLogout,
}: {
  onOpen: (bookId: string) => void;
  onLogout: () => void;
}) {
  const [books, setBooks] = useState<BookStatus[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploadState, setUploadState] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const { items } = await listBooks();
      setBooks(items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Kitaplar yüklenemedi');
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setError(null);
    try {
      setUploadState('Yükleniyor...');
      const bookId = await uploadAndProcess(file, file.name.replace(/\.pdf$/i, ''));
      await pollUntilDone(bookId, (s) =>
        setUploadState(
          s.status === 'processing'
            ? `İşleniyor... %${s.progress_percentage}`
            : `Durum: ${s.status}`,
        ),
      );
      setUploadState(null);
      await refresh();
    } catch (err) {
      setUploadState(null);
      setError(err instanceof ApiError ? err.message : 'Yükleme başarısız');
    }
  };

  return (
    <div style={{ ...panel, maxWidth: 720 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: '1.6em' }}>Kitaplığım</h1>
        <button style={{ ...button, background: '#6b7280' }} onClick={onLogout}>
          Çıkış
        </button>
      </div>

      <label
        style={{
          ...button,
          display: 'inline-block',
          margin: '16px 0',
          background: uploadState ? '#9ca3af' : '#2563eb',
        }}
      >
        {uploadState || 'PDF yükle'}
        <input
          type="file"
          accept="application/pdf"
          onChange={onFile}
          disabled={!!uploadState}
          style={{ display: 'none' }}
        />
      </label>

      {error && <p style={{ color: '#dc2626' }}>{error}</p>}

      {books.length === 0 ? (
        <p style={{ color: '#666' }}>Henüz kitap yok. Bir PDF yükleyerek başla.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {books.map((b) => (
            <li
              key={b.id}
              style={{
                padding: 12,
                border: '1px solid #e5e7eb',
                borderRadius: 6,
                marginBottom: 8,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <strong>{b.title}</strong>
                <div style={{ fontSize: '0.85em', color: '#666' }}>
                  {b.status === 'completed'
                    ? `${b.total_pages} sayfa`
                    : b.status === 'failed'
                    ? `Başarısız: ${b.error_message || ''}`
                    : `${b.status} (%${b.progress_percentage})`}
                </div>
              </div>
              <button
                style={{
                  ...button,
                  background: b.status === 'completed' ? '#2563eb' : '#d1d5db',
                }}
                disabled={b.status !== 'completed'}
                onClick={() => onOpen(b.id)}
              >
                Oku
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reading screen
// ---------------------------------------------------------------------------

function ReadingScreen({ bookId, onBack }: { bookId: string; onBack: () => void }) {
  const [content, setContent] = useState<BookContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState({ pageNumber: 1, blockIndex: 0 });

  useEffect(() => {
    let active = true;
    getBookContent(bookId)
      .then((c) => active && setContent(c))
      .catch((err) =>
        active && setError(err instanceof ApiError ? err.message : 'İçerik yüklenemedi'),
      );
    return () => {
      active = false;
    };
  }, [bookId]);

  const handleProgressChange = useCallback((pageNumber: number, blockIndex: number) => {
    setProgress({ pageNumber, blockIndex });
  }, []);

  if (error) {
    return (
      <div style={panel}>
        <p style={{ color: '#dc2626' }}>{error}</p>
        <button style={button} onClick={onBack}>
          Geri dön
        </button>
      </div>
    );
  }

  if (!content) {
    return (
      <div style={panel}>
        <p>İçerik yükleniyor...</p>
      </div>
    );
  }

  return (
    <div className="App">
      <button
        style={{ ...button, position: 'fixed', top: 10, left: 10, zIndex: 1000, background: '#6b7280' }}
        onClick={onBack}
      >
        ← Kitaplık
      </button>
      <ReaderView
        bookId={content.book_id}
        bookContent={content}
        onProgressChange={handleProgressChange}
      />
      <div
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          background: 'rgba(0,0,0,0.7)',
          color: 'white',
          padding: '5px 10px',
          fontSize: '0.8em',
        }}
      >
        Sayfa {progress.pageNumber}, Blok {progress.blockIndex}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root
// ---------------------------------------------------------------------------

function App() {
  const [view, setView] = useState<View>(
    tokenStore.isAuthenticated ? 'library' : 'auth',
  );
  const [activeBook, setActiveBook] = useState<string | null>(null);

  const handleLogout = async () => {
    await logout();
    setView('auth');
  };

  if (view === 'auth') {
    return <AuthScreen onAuthed={() => setView('library')} />;
  }

  if (view === 'reading' && activeBook) {
    return <ReadingScreen bookId={activeBook} onBack={() => setView('library')} />;
  }

  return (
    <LibraryScreen
      onOpen={(bookId) => {
        setActiveBook(bookId);
        setView('reading');
      }}
      onLogout={handleLogout}
    />
  );
}

export default App;
