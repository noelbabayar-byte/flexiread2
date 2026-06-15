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

// ---------------------------------------------------------------------------
// Shared style tokens
// ---------------------------------------------------------------------------

const colors = {
  primary: '#2563eb',
  primaryDark: '#1d4ed8',
  text: '#0f172a',
  muted: '#64748b',
  border: '#e2e8f0',
  danger: '#dc2626',
  dangerBg: '#fef2f2',
  surface: '#ffffff',
};

const input: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  margin: '6px 0',
  border: `1px solid ${colors.border}`,
  borderRadius: 10,
  fontSize: '0.95rem',
  color: colors.text,
  background: '#f8fafc',
  boxSizing: 'border-box',
};

const button: React.CSSProperties = {
  padding: '12px 18px',
  border: 'none',
  borderRadius: 10,
  background: colors.primary,
  color: 'white',
  cursor: 'pointer',
  fontSize: '0.95rem',
  fontWeight: 600,
};

const errorBox: React.CSSProperties = {
  background: colors.dangerBg,
  color: colors.danger,
  border: `1px solid #fecaca`,
  borderRadius: 10,
  padding: '10px 12px',
  fontSize: '0.9rem',
  margin: '10px 0 0',
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
    <div
      className="fr-screen"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: 'linear-gradient(135deg, #eef2ff 0%, #e0f2fe 100%)',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 420,
          background: colors.surface,
          borderRadius: 18,
          padding: '32px 28px',
          boxShadow: '0 12px 40px rgba(15, 23, 42, 0.12)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: '2rem' }} aria-hidden="true">
            📖
          </span>
        </div>
        <h1
          style={{
            fontSize: '1.7rem',
            textAlign: 'center',
            margin: '0 0 4px',
            color: colors.text,
          }}
        >
          FlexiRead
        </h1>
        <p style={{ color: colors.muted, textAlign: 'center', margin: '0 0 22px' }}>
          {mode === 'login'
            ? 'Hesabına giriş yap ve okumaya devam et'
            : 'Ücretsiz hesabını oluştur'}
        </p>

        <form onSubmit={submit}>
          {mode === 'register' && (
            <input
              className="fr-input"
              style={input}
              placeholder="Ad soyad (opsiyonel)"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          )}
          <input
            className="fr-input"
            style={input}
            type="email"
            placeholder="E-posta"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="fr-input"
            style={input}
            type="password"
            placeholder="Parola (en az 8 karakter)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
          {error && <p style={errorBox}>{error}</p>}
          <button
            className="fr-btn"
            style={{ ...button, width: '100%', marginTop: 14 }}
            disabled={busy}
          >
            {busy && <span className="fr-spinner" aria-hidden="true" />}
            {busy
              ? 'Lütfen bekleyin...'
              : mode === 'login'
              ? 'Giriş'
              : 'Kayıt ol'}
          </button>
        </form>

        <p
          style={{
            marginTop: 20,
            marginBottom: 0,
            fontSize: '0.9rem',
            textAlign: 'center',
            color: colors.muted,
          }}
        >
          {mode === 'login' ? 'Hesabın yok mu? ' : 'Zaten hesabın var mı? '}
          <a
            href="#"
            className="fr-link"
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
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ book }: { book: BookStatus }) {
  const map: Record<string, { label: string; bg: string; fg: string }> = {
    completed: { label: 'Hazır', bg: '#dcfce7', fg: '#166534' },
    processing: {
      label: `İşleniyor %${book.progress_percentage}`,
      bg: '#dbeafe',
      fg: '#1e40af',
    },
    pending: { label: 'Sırada', bg: '#f1f5f9', fg: '#475569' },
    failed: { label: 'Başarısız', bg: '#fee2e2', fg: '#991b1b' },
  };
  const s = map[book.status] || map.pending;
  return (
    <span
      style={{
        display: 'inline-block',
        background: s.bg,
        color: s.fg,
        borderRadius: 999,
        padding: '3px 10px',
        fontSize: '0.75rem',
        fontWeight: 600,
      }}
    >
      {s.label}
    </span>
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

  const busy = !!uploadState;

  return (
    <div className="fr-screen" style={{ background: '#f8fafc' }}>
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '32px 20px 64px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 20,
          }}
        >
          <h1 style={{ fontSize: '1.7rem', margin: 0, color: colors.text }}>
            Kitaplığım
          </h1>
          <button
            className="fr-btn"
            style={{ ...button, background: '#64748b', padding: '9px 14px' }}
            onClick={onLogout}
          >
            Çıkış
          </button>
        </div>

        {/* Upload area */}
        <label
          className="fr-btn"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            padding: '28px 16px',
            marginBottom: 24,
            borderRadius: 14,
            border: `2px dashed ${busy ? '#cbd5e1' : '#bfdbfe'}`,
            background: busy ? '#f1f5f9' : '#eff6ff',
            color: busy ? colors.muted : colors.primaryDark,
            cursor: busy ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            textAlign: 'center',
          }}
        >
          {busy ? (
            <>
              <span className="fr-spinner" style={{ borderTopColor: colors.primary }} aria-hidden="true" />
              <span>{uploadState}</span>
            </>
          ) : (
            <>
              <span style={{ fontSize: '1.6rem' }} aria-hidden="true">
                ⬆️
              </span>
              <span>PDF yükle</span>
              <span style={{ fontWeight: 400, fontSize: '0.82rem', color: colors.muted }}>
                Bir PDF seç, gerisini biz hallederiz
              </span>
            </>
          )}
          <input
            type="file"
            accept="application/pdf"
            onChange={onFile}
            disabled={busy}
            style={{ display: 'none' }}
          />
        </label>

        {error && <p style={errorBox}>{error}</p>}

        {books.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              color: colors.muted,
              padding: '48px 20px',
              border: `1px solid ${colors.border}`,
              borderRadius: 14,
              background: colors.surface,
            }}
          >
            <div style={{ fontSize: '2rem', marginBottom: 8 }} aria-hidden="true">
              📚
            </div>
            Henüz kitap yok. Bir PDF yükleyerek başla.
          </div>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {books.map((b) => (
              <li
                key={b.id}
                className="fr-card"
                style={{
                  padding: 16,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 14,
                  marginBottom: 12,
                  background: colors.surface,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 12,
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <strong
                    style={{
                      display: 'block',
                      color: colors.text,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {b.title}
                  </strong>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginTop: 6,
                      fontSize: '0.85rem',
                      color: colors.muted,
                    }}
                  >
                    <StatusBadge book={b} />
                    {b.status === 'completed' && <span>{b.total_pages} sayfa</span>}
                    {b.status === 'failed' && b.error_message && (
                      <span style={{ color: colors.danger }}>{b.error_message}</span>
                    )}
                  </div>
                </div>
                <button
                  className="fr-btn"
                  style={{
                    ...button,
                    flexShrink: 0,
                    background:
                      b.status === 'completed' ? colors.primary : '#cbd5e1',
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
      <div
        className="fr-screen"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          padding: 24,
        }}
      >
        <p style={errorBox}>{error}</p>
        <button className="fr-btn" style={button} onClick={onBack}>
          ← Kitaplığa dön
        </button>
      </div>
    );
  }

  if (!content) {
    return (
      <div
        className="fr-screen"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: colors.muted,
        }}
      >
        <p>
          <span className="fr-spinner" style={{ borderTopColor: colors.primary }} aria-hidden="true" />
          İçerik yükleniyor...
        </p>
      </div>
    );
  }

  return (
    <div className="App">
      <button
        className="fr-btn"
        style={{
          ...button,
          position: 'fixed',
          top: 12,
          left: 12,
          zIndex: 1000,
          background: 'rgba(15, 23, 42, 0.82)',
          padding: '8px 14px',
        }}
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
