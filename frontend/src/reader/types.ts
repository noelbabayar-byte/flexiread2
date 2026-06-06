/**
 * Updated TypeScript types for Reader Engine
 * Supports modular content blocks: text, image, formula, question
 */

/**
 * Content block types
 */
export type ContentBlockType = 'text' | 'image' | 'formula' | 'question';

export type ReaderTheme = 'light' | 'dark' | 'sepia';

/**
 * Modular content block
 * Replaces simple string paragraphs
 */
export interface ContentBlock {
  id: string; // Unique identifier for this block
  type: ContentBlockType;
  content: string; // Text, LaTeX formula, or S3 image URL
  metadata?: {
    original_bounding_box?: [number, number, number, number]; // [x, y, width, height]
    confidence?: number; // OCR confidence (0-1)
    language?: string; // Detected language
    source?: 'native' | 'ocr'; // Original or OCR'd
  };
}

/**
 * Section/Chapter metadata for TOC
 */
export interface Section {
  id: string;
  title: string;
  startPageNumber: number;
  startBlockIndex: number; // Index of first block on this page
  level: number; // 1=chapter, 2=section, 3=subsection
}

/**
 * Page containing modular blocks
 */
export interface PageData {
  page_number: number;
  blocks: ContentBlock[]; // Array of modular blocks (replaces paragraphs)
  is_ocr: boolean;
  confidence?: number;
}

/**
 * Reading preferences
 */
export interface ReadingPreferences {
  fontSize: number; // 14-28px
  theme: 'light' | 'dark' | 'sepia';
  lineHeight: 'small' | 'medium' | 'large';
  fontFamily: 'serif' | 'sans-serif' | 'monospace';
  imageScale?: number; // 0.5-1.5 (image zoom)
  formulaSize?: number; // 0.8-1.2 (formula zoom)
}

/**
 * Book content from backend
 */
export interface BookContent {
  book_id: string;
  total_pages: number;
  pages: PageData[];
  sections?: Section[]; // Table of contents
  metadata?: {
    title: string;
    author?: string;
    total_words?: number;
    language?: string;
  };
}

/**
 * Reading progress
 */
export interface ReadingProgress {
  bookId: string;
  currentPageNumber: number;
  currentBlockIndex: number; // Index of visible block (replaces paragraphIndex)
  scrollPosition: number;
  lastUpdated: number;
}

/**
 * Visible block entry (for IntersectionObserver)
 */
export interface VisibleBlockEntry {
  pageNumber: number;
  blockIndex: number;
  blockId: string;
  visibilityPercentage: number;
}

/**
 * Virtual scroll state
 */
export interface VirtualScrollState {
  startPageIndex: number;
  endPageIndex: number;
  bufferSize: number;
  totalPages: number;
}

/**
 * Complete reader state
 */
export interface ReaderState {
  bookContent: BookContent | null;
  preferences: ReadingPreferences;
  progress: ReadingProgress;
  virtualScroll: VirtualScrollState;
  isLoading: boolean;
  error: string | null;
}

/**
 * Render context for ContentBlock
 */
export interface RenderContext {
  preferences: ReadingPreferences;
  pageNumber: number;
  blockIndex: number;
  isOCR: boolean;
}

// Backward compatibility
export interface VisibleParagraphEntry {
  pageNumber: number;
  paragraphIndex: number;
  visibilityPercentage: number;
}
