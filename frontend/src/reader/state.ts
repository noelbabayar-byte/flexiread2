/**
 * Reactive state management for Reader Engine
 * Manages preferences, progress, and virtual scroll state
 * Emits events when state changes
 */

import {
  ReaderState,
  ReadingPreferences,
  ReadingProgress,
  BookContent,
} from './types';
import { ReaderStorage } from './storage';

type StateChangeListener = (state: ReaderState) => void;
type PreferenceChangeListener = (prefs: ReadingPreferences) => void;
type ProgressChangeListener = (progress: ReadingProgress) => void;

/**
 * Reactive state manager
 */
export class ReaderStateManager {
  private state: ReaderState;
  private stateListeners: Set<StateChangeListener> = new Set();
  private preferenceListeners: Set<PreferenceChangeListener> = new Set();
  private progressListeners: Set<ProgressChangeListener> = new Set();

  constructor(bookId: string) {
    // Load saved preferences or use defaults
    const savedPrefs = ReaderStorage.loadPreferences();
    const defaultPreferences: ReadingPreferences = {
      fontSize: 16,
      theme: 'light',
      lineHeight: 'medium',
      fontFamily: 'serif',
    };

    // Load saved progress or use defaults
    const savedProgress = ReaderStorage.loadProgress(bookId);
    const defaultProgress: ReadingProgress = {
      bookId,
      currentPageNumber: 1,
      currentBlockIndex: 0,
      scrollPosition: 0,
      lastUpdated: Date.now(),
    };

    // Initialize state
    this.state = {
      bookContent: null,
      preferences: savedPrefs || defaultPreferences,
      progress: savedProgress || defaultProgress,
      virtualScroll: {
        startPageIndex: 0,
        endPageIndex: 2, // Buffer: 3 pages (0, 1, 2)
        bufferSize: 3,
        totalPages: 0,
      },
      isLoading: false,
      error: null,
    };
  }

  /**
   * Get current state
   * Deep copy to prevent external mutation
   */
  getState(): ReaderState {
    return JSON.parse(JSON.stringify(this.state));
  }

  /**
   * Set book content
   */
  setBookContent(content: BookContent): void {
    this.state.bookContent = content;
    this.state.virtualScroll.totalPages = content.total_pages;
    this.state.isLoading = false;
    this.emitStateChange();
  }

  /**
   * Update reading preferences
   * Triggers CSS variable updates via listeners
   */
  updatePreferences(updates: Partial<ReadingPreferences>): void {
    const newPrefs = { ...this.state.preferences, ...updates };
    this.state.preferences = newPrefs;

    // Persist to localStorage
    ReaderStorage.savePreferences(newPrefs);

    // Notify listeners
    this.emitPreferenceChange();
    this.emitStateChange();
  }

  /**
   * Update reading progress
   * Called when user scrolls
   */
  updateProgress(updates: Partial<ReadingProgress>): void {
    this.state.progress = {
      ...this.state.progress,
      ...updates,
      lastUpdated: Date.now(),
    };

    // Notify listeners (progress listeners handle debouncing)
    this.emitProgressChange();
  }

  /**
   * Update virtual scroll window
   * Called when user scrolls and pages need to be loaded/unloaded
   */
  updateVirtualScroll(startPageIndex: number, endPageIndex: number): void {
    if (this.state.virtualScroll.totalPages <= 0) return;

    this.state.virtualScroll = {
      ...this.state.virtualScroll,
      startPageIndex: Math.max(0, startPageIndex),
      endPageIndex: Math.min(
        this.state.virtualScroll.totalPages - 1,
        endPageIndex
      ),
    };

    this.emitStateChange();
  }

  /**
   * Set loading state
   */
  setLoading(isLoading: boolean): void {
    this.state.isLoading = isLoading;
    this.emitStateChange();
  }

  /**
   * Set error state
   */
  setError(error: string | null): void {
    this.state.error = error;
    this.emitStateChange();
  }

  /**
   * Reset progress to beginning
   */
  resetProgress(): void {
    this.state.progress = {
      ...this.state.progress,
      currentPageNumber: 1,
      currentBlockIndex: 0,
      scrollPosition: 0,
      lastUpdated: Date.now(),
    };

    ReaderStorage.saveProgress(
      this.state.progress.bookId,
      this.state.progress
    );
    this.emitProgressChange();
  }

  /**
   * Subscribe to state changes
   */
  onStateChange(listener: StateChangeListener): () => void {
    this.stateListeners.add(listener);

    // Return unsubscribe function
    return () => {
      this.stateListeners.delete(listener);
    };
  }

  /**
   * Subscribe to preference changes
   */
  onPreferenceChange(listener: PreferenceChangeListener): () => void {
    this.preferenceListeners.add(listener);
    return () => {
      this.preferenceListeners.delete(listener);
    };
  }

  /**
   * Subscribe to progress changes
   */
  onProgressChange(listener: ProgressChangeListener): () => void {
    this.progressListeners.add(listener);
    return () => {
      this.progressListeners.delete(listener);
    };
  }

  /**
   * Emit state change event
   */
  private emitStateChange(): void {
    const state = this.getState();
    this.stateListeners.forEach((listener) => listener(state));
  }

  /**
   * Emit preference change event
   */
  private emitPreferenceChange(): void {
    this.preferenceListeners.forEach((listener) =>
      listener(this.state.preferences)
    );
  }

  /**
   * Emit progress change event
   */
  private emitProgressChange(): void {
    this.progressListeners.forEach((listener) =>
      listener(this.state.progress)
    );
  }
}

/**
 * Create global state manager instance
 */
let stateManager: ReaderStateManager | null = null;

export function initializeStateManager(bookId: string): ReaderStateManager {
  stateManager = new ReaderStateManager(bookId);
  return stateManager;
}

export function getStateManager(): ReaderStateManager {
  if (!stateManager) {
    throw new Error('State manager not initialized. Call initializeStateManager first.');
  }
  return stateManager;
}
