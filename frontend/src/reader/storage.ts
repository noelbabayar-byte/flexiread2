/**
 * Storage layer for reader preferences and progress
 * localStorage: preferences (small, frequently accessed)
 * IndexedDB: book content (large, optional caching)
 */

import { ReadingPreferences, ReadingProgress } from './types';

const STORAGE_KEYS = {
  PREFERENCES: 'flexiread:preferences',
  PROGRESS_PREFIX: 'flexiread:progress:',
};

const DB_NAME = 'flexiread-db';
const STORE_NAME = 'books';

export class ReaderStorage {
  /**
   * Save reading preferences to localStorage
   */
  static savePreferences(preferences: ReadingPreferences): void {
    try {
      localStorage.setItem(
        STORAGE_KEYS.PREFERENCES,
        JSON.stringify(preferences)
      );
      console.debug('Preferences saved');
    } catch (e) {
      console.error('Failed to save preferences:', e);
    }
  }

  /**
   * Load reading preferences from localStorage
   */
  static loadPreferences(): ReadingPreferences | null {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.PREFERENCES);
      return stored ? JSON.parse(stored) : null;
    } catch (e) {
      console.error('Failed to load preferences:', e);
      return null;
    }
  }

  /**
   * Save reading progress (debounced)
   */
  static saveProgress(bookId: string, progress: ReadingProgress): void {
    try {
      const key = `${STORAGE_KEYS.PROGRESS_PREFIX}${bookId}`;
      localStorage.setItem(key, JSON.stringify(progress));
    } catch (e) {
      console.error('Failed to save progress:', e);
    }
  }

  /**
   * Load reading progress
   */
  static loadProgress(bookId: string): ReadingProgress | null {
    try {
      const key = `${STORAGE_KEYS.PROGRESS_PREFIX}${bookId}`;
      const stored = localStorage.getItem(key);
      return stored ? JSON.parse(stored) : null;
    } catch (e) {
      console.error('Failed to load progress:', e);
      return null;
    }
  }

  /**
   * Clear progress for a book
   */
  static clearProgress(bookId: string): void {
    try {
      const key = `${STORAGE_KEYS.PROGRESS_PREFIX}${bookId}`;
      localStorage.removeItem(key);
    } catch (e) {
      console.error('Failed to clear progress:', e);
    }
  }

  /**
   * Initialize IndexedDB
   */
  static async initDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 1);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'book_id' });
        }
      };
    });
  }

  /**
   * Cache book content in IndexedDB
   */
  static async cacheBookContent(bookId: string, content: any): Promise<void> {
    try {
      const db = await this.initDB();
      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);

      await new Promise<void>((resolve, reject) => {
        const request = store.put({
          book_id: bookId,
          content,
          timestamp: Date.now(),
        });
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
      });
    } catch (e) {
      console.warn('IndexedDB caching failed:', e);
    }
  }

  /**
   * Retrieve cached book content
   */
  static async getCachedBookContent(bookId: string): Promise<any | null> {
    try {
      const db = await this.initDB();
      const transaction = db.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);

      return new Promise<any>((resolve, reject) => {
        const request = store.get(bookId);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
          const result = request.result;
          resolve(result ? result.content : null);
        };
      });
    } catch (e) {
      console.warn('IndexedDB retrieval failed:', e);
      return null;
    }
  }

  /**
   * Clear all cache
   */
  static async clearAllCache(): Promise<void> {
    try {
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith('flexiread:')) {
          localStorage.removeItem(key);
        }
      });

      const db = await this.initDB();
      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);

      await new Promise<void>((resolve, reject) => {
        const request = store.clear();
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
      });
    } catch (e) {
      console.error('Failed to clear cache:', e);
    }
  }
}

/**
 * Debounce helper for progress saving
 */
export function createDebouncedProgressSaver(
  delay: number = 2000
): (bookId: string, progress: ReadingProgress) => void {
  const timers = new Map<string, NodeJS.Timeout>();

  return (bookId: string, progress: ReadingProgress) => {
    if (timers.has(bookId)) {
      clearTimeout(timers.get(bookId)!);
    }

    const timer = setTimeout(() => {
      ReaderStorage.saveProgress(bookId, progress);
      timers.delete(bookId);
    }, delay);

    timers.set(bookId, timer);
  };
}
