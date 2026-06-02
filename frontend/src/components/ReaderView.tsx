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

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { ReaderEngine, initializeEngine, getEngine } from '@/reader/engine';
import { ReaderStateManager, initializeStateManager, getStateManager } from '@/reader/state';
import { BookContent, PageData } from '@/reader/types';
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

  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showTOC, setShowTOC] = useState(false);

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
        pageElements.forEach((el) => contentDiv.appendChild(el));
      }

      // Listen to progress changes
      stateManager.onProgressChange((progress) => {
        if (onProgressChange) {
          onProgressChange(progress.currentPageNumber, progress.currentBlockIndex);
        }
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
  }, [bookId, bookContent, onProgressChange]);

  /**
   * Handle settings panel changes
   */
  const handlePreferenceChange = (preferences: any) => {
    if (stateManagerRef.current) {
      stateManagerRef.current.updatePreferences(preferences);
    }
  };

  /**
   * Handle TOC section click
   */
  const handleSectionClick = (sectionId: string) => {
    if (engineRef.current) {
      engineRef.current.scrollToBlock(sectionId, true);
      setShowTOC(false);
    }
  };

  /**
   * Handle page navigation
   */
  const handleGoToPage = (pageNumber: number) => {
    if (engineRef.current) {
      engineRef.current.scrollToPage(pageNumber, true);
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
        data-theme="light"
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
        onPreferenceChange={handlePreferenceChange}
        stateManager={stateManagerRef.current}
      />

      {/* Table of Contents - React component */}
      <TableOfContents
        isOpen={showTOC}
        onClose={() => setShowTOC(false)}
        onSectionClick={handleSectionClick}
        onPageClick={handleGoToPage}
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
