/**
 * Updated Reader Engine: ContentBlock Rendering + ScrollTo
 * Handles text, image, formula, and question blocks
 * Isolated from React via useRef strategy
 */

import { getStateManager } from './state';
import { ReaderStorage, createDebouncedProgressSaver } from './storage';
import { VisibleBlockEntry, ContentBlock, PageData } from './types';

const BUFFER_SIZE = 3;

/**
 * Reader Engine with ContentBlock support
 */
export class ReaderEngine {
  private container: HTMLElement;
  private stateManager = getStateManager();
  private intersectionObserver: IntersectionObserver | null = null;
  private visibleBlocks: Map<string, VisibleBlockEntry> = new Map();
  private mostVisibleBlock: VisibleBlockEntry | null = null;
  private debouncedProgressSaver = createDebouncedProgressSaver(2000);
  private resizeObserver: ResizeObserver | null = null;
  private isRestoring = false;
  private blockRegistry: Map<string, HTMLElement> = new Map(); // blockId -> DOM element

  constructor(containerSelector: string) {
    const container = document.querySelector(containerSelector);
    if (!container) {
      throw new Error(`Container not found: ${containerSelector}`);
    }
    this.container = container as HTMLElement;
    this.setupIntersectionObserver();
    this.setupResizeObserver();
    this.setupScrollListener();
  }

  /**
   * Initialize reader
   */
  async initialize(): Promise<void> {
    this.restoreScrollPosition();

    this.stateManager.onStateChange((state) => {
      this.updateVirtualScroll();
    });

    this.stateManager.onPreferenceChange(() => {
      this.applyPreferences();
    });
  }

  /**
   * Render ContentBlock to DOM
   * Handles: text, image, formula, question
   */
  private renderContentBlock(
    block: ContentBlock,
    pageNumber: number,
    blockIndex: number
  ): HTMLElement {
    const blockElement = document.createElement('div');
    blockElement.className = `reader-block reader-block-${block.type}`;
    blockElement.dataset.blockId = block.id;
    blockElement.dataset.pageNumber = pageNumber.toString();
    blockElement.dataset.blockIndex = blockIndex.toString();

    // Register block for tracking
    this.blockRegistry.set(block.id, blockElement);

    switch (block.type) {
      case 'text':
        return this.renderTextBlock(blockElement, block, pageNumber, blockIndex);

      case 'image':
        return this.renderImageBlock(blockElement, block, pageNumber, blockIndex);

      case 'formula':
        return this.renderFormulaBlock(blockElement, block, pageNumber, blockIndex);

      case 'question':
        return this.renderQuestionBlock(blockElement, block, pageNumber, blockIndex);

      default:
        blockElement.textContent = `[Unknown block type: ${block.type}]`;
        return blockElement;
    }
  }

  /**
   * Render text block
   */
  private renderTextBlock(
    element: HTMLElement,
    block: ContentBlock,
    pageNumber: number,
    blockIndex: number
  ): HTMLElement {
    element.className = `reader-paragraph ${
      block.metadata?.source === 'ocr' ? 'ocr' : ''
    }`;
    element.textContent = block.content;

    // Add OCR indicator if needed
    if (block.metadata?.source === 'ocr' && block.metadata?.confidence) {
      const confidence = Math.round(block.metadata.confidence * 100);
      element.title = `OCR confidence: ${confidence}%`;
    }

    return element;
  }

  /**
   * Render image block
   */
  private renderImageBlock(
    element: HTMLElement,
    block: ContentBlock,
    pageNumber: number,
    blockIndex: number
  ): HTMLElement {
    element.className = 'reader-image-block';

    const img = document.createElement('img');
    img.src = block.content; // S3 URL
    img.alt = `Image from page ${pageNumber}`;
    img.className = 'reader-image';

    // Apply image scale preference
    const preferences = this.stateManager.getState().preferences;
    const scale = preferences.imageScale || 1;
    img.style.maxWidth = `${100 * scale}%`;

    element.appendChild(img);
    return element;
  }

  /**
   * Render formula block (LaTeX)
   */
  private renderFormulaBlock(
    element: HTMLElement,
    block: ContentBlock,
    pageNumber: number,
    blockIndex: number
  ): HTMLElement {
    element.className = 'reader-formula-block';

    const formula = document.createElement('div');
    formula.className = 'reader-formula';
    formula.textContent = block.content; // LaTeX string

    // Apply formula size preference
    const preferences = this.stateManager.getState().preferences;
    const formulaSize = preferences.formulaSize || 1;
    formula.style.fontSize = `${100 * formulaSize}%`;

    // TODO: Integrate MathJax or KaTeX for rendering
    // For now, show as code block
    formula.style.fontFamily = 'monospace';
    formula.style.backgroundColor = 'rgba(0,0,0,0.05)';
    formula.style.padding = '0.5em';
    formula.style.borderRadius = '4px';

    element.appendChild(formula);
    return element;
  }

  /**
   * Render question block (for academic content)
   */
  private renderQuestionBlock(
    element: HTMLElement,
    block: ContentBlock,
    pageNumber: number,
    blockIndex: number
  ): HTMLElement {
    element.className = 'reader-question-block';

    const questionContainer = document.createElement('div');
    questionContainer.className = 'reader-question-container';

    const questionIcon = document.createElement('span');
    questionIcon.className = 'reader-question-icon';
    questionIcon.textContent = '❓';

    const questionText = document.createElement('p');
    questionText.className = 'reader-question-text';
    questionText.textContent = block.content;

    questionContainer.appendChild(questionIcon);
    questionContainer.appendChild(questionText);
    element.appendChild(questionContainer);

    return element;
  }

  /**
   * Setup IntersectionObserver for block visibility tracking
   */
  private setupIntersectionObserver(): void {
    const options: IntersectionObserverInit = {
      root: this.container,
      threshold: [0, 0.25, 0.5, 0.75, 1.0],
      rootMargin: '-50px 0px -50px 0px',
    };

    this.intersectionObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const element = entry.target as HTMLElement;
        const blockId = element.dataset.blockId || '';
        const pageNum = parseInt(element.dataset.pageNumber || '0');
        const blockIdx = parseInt(element.dataset.blockIndex || '0');

        if (entry.isIntersecting) {
          const visibilityPercentage = Math.round(entry.intersectionRatio * 100);

          this.visibleBlocks.set(blockId, {
            pageNumber: pageNum,
            blockIndex: blockIdx,
            blockId,
            visibilityPercentage,
          });

          // Track most visible block
          if (
            !this.mostVisibleBlock ||
            visibilityPercentage > this.mostVisibleBlock.visibilityPercentage
          ) {
            this.mostVisibleBlock = {
              pageNumber: pageNum,
              blockIndex: blockIdx,
              blockId,
              visibilityPercentage,
            };
          }
        } else {
          this.visibleBlocks.delete(blockId);
        }
      });

      // Update progress
      if (this.mostVisibleBlock) {
        this.stateManager.updateProgress({
          currentPageNumber: this.mostVisibleBlock.pageNumber,
          currentBlockIndex: this.mostVisibleBlock.blockIndex,
          scrollPosition: this.calculateScrollPercentage(),
        });
      }
    });
  }

  /**
   * Setup ResizeObserver for orientation changes
   */
  private setupResizeObserver(): void {
    this.resizeObserver = new ResizeObserver(() => {
      if (!this.isRestoring) {
        setTimeout(() => {
          this.restoreScrollPosition();
        }, 100);
      }
    });

    this.resizeObserver.observe(this.container);
  }

  /**
   * Setup scroll listener
   */
  private setupScrollListener(): void {
    let scrollTimeout: NodeJS.Timeout | null = null;

    this.container.addEventListener('scroll', () => {
      if (scrollTimeout) clearTimeout(scrollTimeout);

      scrollTimeout = setTimeout(() => {
        this.updateVirtualScroll();
      }, 100);
    });
  }

  /**
   * Update virtual scroll window
   */
  private updateVirtualScroll(): void {
    const state = this.stateManager.getState();
    if (!state.bookContent) return;

    const scrollTop = this.container.scrollTop;
    const containerHeight = this.container.clientHeight;
    const totalHeight = this.container.scrollHeight;

    const scrollPercentage = scrollTop / (totalHeight - containerHeight);
    const estimatedPageIndex = Math.floor(
      scrollPercentage * state.bookContent.total_pages
    );

    const startPageIndex = Math.max(0, estimatedPageIndex - 1);
    const endPageIndex = Math.min(
      state.bookContent.total_pages - 1,
      estimatedPageIndex + 1
    );

    this.stateManager.updateVirtualScroll(startPageIndex, endPageIndex);
    this.pruneOutOfBufferBlocks(startPageIndex, endPageIndex);
  }

  /**
   * Remove blocks outside virtual scroll buffer
   */
  private pruneOutOfBufferBlocks(
    startPageIndex: number,
    endPageIndex: number
  ): void {
    const blocks = this.container.querySelectorAll('[data-page-number]');

    blocks.forEach((block) => {
      const pageNum = parseInt(block.getAttribute('data-page-number') || '0');

      if (pageNum < startPageIndex || pageNum > endPageIndex) {
        const blockId = block.getAttribute('data-block-id');
        if (blockId) {
          this.blockRegistry.delete(blockId);
        }
        block.remove();
      }
    });
  }

  /**
   * Restore scroll position after orientation change
   */
  private restoreScrollPosition(): void {
    this.isRestoring = true;

    const state = this.stateManager.getState();
    const { currentPageNumber, currentBlockIndex } = state.progress;

    const targetElement = this.container.querySelector(
      `[data-page-number="${currentPageNumber}"][data-block-index="${currentBlockIndex}"]`
    );

    if (targetElement) {
      targetElement.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });

      console.debug(
        `Restored scroll to page ${currentPageNumber}, block ${currentBlockIndex}`
      );
    }

    setTimeout(() => {
      this.isRestoring = false;
    }, 500);
  }

  /**
   * Apply reading preferences
   */
  private applyPreferences(): void {
    const state = this.stateManager.getState();
    const { fontSize, theme, lineHeight, fontFamily } = state.preferences;

    const lineHeightMap = {
      small: '1.4',
      medium: '1.6',
      large: '1.8',
    };

    const fontFamilyMap = {
      serif: '"Georgia", serif',
      'sans-serif': '"Segoe UI", sans-serif',
      monospace: '"Courier New", monospace',
    };

    this.container.style.setProperty('--reader-font-size', `${fontSize}px`);
    this.container.style.setProperty(
      '--reader-line-height',
      lineHeightMap[lineHeight]
    );
    this.container.style.setProperty(
      '--reader-font-family',
      fontFamilyMap[fontFamily]
    );
    this.container.style.setProperty('--reader-theme', theme);
  }

  /**
   * Calculate scroll position as percentage
   */
  private calculateScrollPercentage(): number {
    const scrollTop = this.container.scrollTop;
    const containerHeight = this.container.clientHeight;
    const totalHeight = this.container.scrollHeight;

    const scrollableHeight = totalHeight - containerHeight;
    return scrollableHeight > 0 ? (scrollTop / scrollableHeight) * 100 : 0;
  }

  /**
   * Observe a block element
   */
  observeBlock(element: HTMLElement): void {
    if (this.intersectionObserver) {
      this.intersectionObserver.observe(element);
    }
  }

  /**
   * Unobserve a block element
   */
  unobserveBlock(element: HTMLElement): void {
    if (this.intersectionObserver) {
      this.intersectionObserver.unobserve(element);
    }
  }

  /**
   * Scroll to a specific block by ID
   * Used by TableOfContents
   */
  scrollToBlock(blockId: string, smooth: boolean = true): void {
    const element = this.blockRegistry.get(blockId);

    if (element) {
      element.scrollIntoView({
        behavior: smooth ? 'smooth' : 'auto',
        block: 'start',
      });

      console.debug(`Scrolled to block: ${blockId}`);
    } else {
      console.warn(`Block not found: ${blockId}`);
    }
  }

  /**
   * Scroll to a specific page
   */
  scrollToPage(pageNumber: number, smooth: boolean = true): void {
    const element = this.container.querySelector(
      `[data-page-number="${pageNumber}"]`
    );

    if (element) {
      element.scrollIntoView({
        behavior: smooth ? 'smooth' : 'auto',
        block: 'start',
      });

      console.debug(`Scrolled to page: ${pageNumber}`);
    }
  }

  /**
   * Render visible pages
   * Called by React component
   */
  renderVisiblePages(pages: PageData[]): HTMLElement[] {
    const elements: HTMLElement[] = [];

    pages.forEach((page) => {
      const pageElement = document.createElement('div');
      pageElement.className = 'reader-page';
      pageElement.dataset.pageNumber = page.page_number.toString();

      page.blocks.forEach((block, blockIndex) => {
        const blockElement = this.renderContentBlock(
          block,
          page.page_number,
          blockIndex
        );

        // Observe for visibility tracking
        this.observeBlock(blockElement);

        pageElement.appendChild(blockElement);
      });

      elements.push(pageElement);
    });

    return elements;
  }

  /**
   * Save progress
   */
  saveProgress(): void {
    const state = this.stateManager.getState();
    this.debouncedProgressSaver(state.progress.bookId, state.progress);
  }

  /**
   * Cleanup
   */
  destroy(): void {
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    this.blockRegistry.clear();
  }
}

/**
 * Global engine instance
 */
let engine: ReaderEngine | null = null;

export function initializeEngine(containerSelector: string): ReaderEngine {
  engine = new ReaderEngine(containerSelector);
  return engine;
}

export function getEngine(): ReaderEngine {
  if (!engine) {
    throw new Error('Engine not initialized. Call initializeEngine first.');
  }
  return engine;
}
