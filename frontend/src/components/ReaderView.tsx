/**
 * ReaderView Component
 * React <-> Vanilla Engine Isolation via useRef
 * 
 * Strategy:
 * - React only manages outer container and state changes
 * - Vanilla Engine has exclusive control over DOM inside ref.current
 * - React never re-renders the reader content div
 * - State changes (font, theme) are passed to Engine via callbacks
 */

import React, { useEffect, useRef, useState } from 'react';
import { ReaderEngine, initializeEngine, getEngine } from '@/reader/engine';
import { ReaderStateManager, initializeStateManager, getStateManager } from '@/reader/state';
import { BookContent, PageData, ReadingPreferences } from '@/reader/types';
import SettingsPanel from './SettingsPanel';
import TableOfContents from './TableOfContents';
import '@/reader/styles.css';

interface ReaderViewProps {
  bookId: string;
  bookContent: BookContent;
  onProgressChange?: (pageNumber: number, blockIndex: number) => void;
}

/**
 * ReaderView Component
 */
export const ReaderView: React.FC<ReaderViewProps> = ({
  bookId,
  bookContent,
  onProgressChange,
}) => {
  const readerContainerRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<ReaderEngine | null>(null);
  const stateManagerRef = useRef<ReaderStateManager | null>(null);
  // Ref to avoid re-running the init effect when the parent passes a new callback reference.
  const onProgressChangeRef = useRef(onProgressChange);
  onProgressChangeRef.current = onProgressChange;

  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showTOC, setShowTOC] = useState(false);
  const [preferences, setPreferences] = useState<ReadingPreferences>({
    fontSize: 16,
    theme: 'light',
    lineHeight: 'medium',
    fontFamily: 'serif',
    imageScale: 1,
    formulaSize: 1,
  });

  /**
   * Initialize Engine and State Manager
   * This runs once on mount
   */
  useEffect(() => {
    if (!readerContainerRef.current) return;

    try {
      // Initialize state manager
      const stateManager = initializeStateManager(bookId);
      stateManager.setBookContent(bookContent);
      stateManagerRef.current = stateManager;
      setPreferences(stateManager.getState().preferences);

      // Initialize engine (Vanilla DOM controller)
      const engine = initializeEngine('.reader-container');
      engineRef.current = engine;

      // Initialize engine
      engine.initialize();

      // Render initial visible pages
      const state = stateManager.getState();
      const visiblePages = bookContent.pages.slice(
        state.virtualScroll.startPageIndex,
        state.virtualScroll.endPageIndex + 1
      );

      const pageElements = engine.renderVisiblePages(visiblePages);
      const contentDiv = readerContainerRef.current.querySelector('.reader-content');

      if (contentDiv) {
        contentDiv.innerHTML = '';
        if (pageElements.length === 0) {
          console.warn('No pages to render initially');
        }
        pageElements.forEach((el) => contentDiv.appendChild(el));
      } else {
        console.error('Reader content div not found in DOM');
      }

      // Listen to progress changes – read latest callback from ref so the
      // effect doesn't re-run when the parent passes a new function reference.
      stateManager.onProgressChange((progress) => {
        const cb = onProgressChangeRef.current;
        if (cb) {
          cb(progress.currentPageNumber, progress.currentBlockIndex);
        }
      });

      // Listen to preference changes to update local state
      stateManager.onPreferenceChange((newPrefs) => {
        setPreferences(newPrefs);
      });

      setIsInitialized(true);
      setIsLoading(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to initialize reader';
      setError(errorMessage);
      setIsLoading(false);
      console.error('Reader initialization error:', err);
    }

    // Cleanup on unmount
    return () => {
      if (engineRef.current) {
        engineRef.current.destroy();
      }
    };
  // Intentionally omit onProgressChange from deps – we read the latest
  // callback via onProgressChangeRef so parent re-renders don't destroy
  // and recreate the engine.
  }, [bookId, bookContent]);

  /**
   * Handle settings panel changes
   */
  const handlePreferenceChange = (newPrefs: Partial<ReadingPreferences>) => {
    if (stateManagerRef.current) {
      stateManagerRef.current.updatePreferences(newPrefs);
    }
  };

  if (isLoading) {
    return (
      <div className="reader-loading">
        <div>Loading book...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="reader-error">
        <h2>Error loading book</h2>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="reader-wrapper">
      {/* Main reader container - Vanilla Engine controls DOM inside */}
      <div
        ref={readerContainerRef}
        className="reader-container"
        data-theme={preferences.theme}
      >
        <div className="reader-content">
          {/* Engine renders pages here */}
        </div>

        {/* Progress bar */}
        <div className="reader-progress" />
      </div>

      {/* Settings Panel - React component */}
      <SettingsPanel
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        currentTheme={preferences.theme}
        currentFontSize={preferences.fontSize}
        currentLineHeight={preferences.lineHeight}
        currentFontFamily={preferences.fontFamily}
        currentImageScale={preferences.imageScale || 1}
        currentFormulaSize={preferences.formulaSize || 1}
        onThemeChange={(theme) => handlePreferenceChange({ theme })}
        onFontSizeChange={(fontSize) => handlePreferenceChange({ fontSize })}
        onLineHeightChange={(lineHeight) => handlePreferenceChange({ lineHeight })}
        onFontFamilyChange={(fontFamily) => handlePreferenceChange({ fontFamily })}
        onImageScaleChange={(imageScale) => handlePreferenceChange({ imageScale })}
        onFormulaSizeChange={(formulaSize) => handlePreferenceChange({ formulaSize })}
      />

      {/* Table of Contents - React component */}
      <TableOfContents
        isOpen={showTOC}
        onClose={() => setShowTOC(false)}
        bookContent={bookContent}
      />

      {/* Control buttons */}
      <div className="reader-controls">
        <button
          className="reader-control-btn"
          onClick={() => setShowSettings(!showSettings)}
          title="Reading preferences"
        >
          ⚙️
        </button>
        <button
          className="reader-control-btn"
          onClick={() => setShowTOC(!showTOC)}
          title="Table of contents"
        >
          📑
        </button>
      </div>
    </div>
  );
};

export default ReaderView;
