/**
 * TableOfContents Component
 * Displays book sections and allows navigation
 * Supports hierarchical sections (chapters, sections, subsections)
 */

import React, { useMemo } from 'react';
import { BookContent, Section } from '@/reader/types';

interface TableOfContentsProps {
  isOpen: boolean;
  onClose: () => void;
  onSectionClick: (sectionId: string) => void;
  onPageClick: (pageNumber: number) => void;
  bookContent: BookContent;
}

/**
 * TableOfContents Component
 */
export const TableOfContents: React.FC<TableOfContentsProps> = ({
  isOpen,
  onClose,
  onSectionClick,
  onPageClick,
  bookContent,
}) => {
  /**
   * Generate sections if not provided
   * Fallback: create sections from pages
   */
  const sections = useMemo(() => {
    if (bookContent.sections && bookContent.sections.length > 0) {
      return bookContent.sections;
    }

    // Fallback: create simple sections from pages
    const fallbackSections: Section[] = [];
    bookContent.pages.forEach((page, idx) => {
      if (idx % 10 === 0) {
        // Create a section every 10 pages
        fallbackSections.push({
          id: `page-${page.page_number}`,
          title: `Page ${page.page_number}`,
          startPageNumber: page.page_number,
          startBlockIndex: 0,
          level: 1,
        });
      }
    });

    return fallbackSections.length > 0
      ? fallbackSections
      : [
          {
            id: 'start',
            title: 'Start',
            startPageNumber: 1,
            startBlockIndex: 0,
            level: 1,
          },
        ];
  }, [bookContent]);

  /**
   * Group sections by level for hierarchical display
   */
  const groupedSections = useMemo(() => {
    const groups: { [key: number]: Section[] } = {};

    sections.forEach((section) => {
      if (!groups[section.level]) {
        groups[section.level] = [];
      }
      groups[section.level].push(section);
    });

    return groups;
  }, [sections]);

  /**
   * Render section item
   */
  const renderSectionItem = (section: Section) => {
    const paddingLeft = `${(section.level - 1) * 1.5}rem`;

    return (
      <div
        key={section.id}
        className="reader-toc-item"
        style={{ paddingLeft }}
      >
        <button
          className="reader-toc-link"
          onClick={() => {
            onSectionClick(section.id);
            onPageClick(section.startPageNumber);
          }}
        >
          <span className="reader-toc-title">{section.title}</span>
          <span className="reader-toc-page">p. {section.startPageNumber}</span>
        </button>
      </div>
    );
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="reader-toc-overlay" onClick={onClose}>
      <div
        className="reader-toc-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="reader-toc-header">
          <h2>Table of Contents</h2>
          <button className="reader-toc-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="reader-toc-content">
          {sections.length === 0 ? (
            <div className="reader-toc-empty">
              <p>No table of contents available</p>
            </div>
          ) : (
            <div className="reader-toc-list">
              {/* Book metadata */}
              {bookContent.metadata && (
                <div className="reader-toc-metadata">
                  <h3>{bookContent.metadata.title}</h3>
                  {bookContent.metadata.author && (
                    <p className="reader-toc-author">
                      by {bookContent.metadata.author}
                    </p>
                  )}
                  <p className="reader-toc-stats">
                    {bookContent.total_pages} pages
                    {bookContent.metadata.total_words &&
                      ` • ${(bookContent.metadata.total_words / 1000).toFixed(0)}k words`}
                  </p>
                </div>
              )}

              {/* Sections */}
              {sections.map((section) => renderSectionItem(section))}

              {/* Quick page navigation */}
              <div className="reader-toc-divider" />
              <div className="reader-toc-quick-nav">
                <label className="reader-toc-label">Go to page:</label>
                <input
                  type="number"
                  className="reader-toc-input"
                  min="1"
                  max={bookContent.total_pages}
                  placeholder="Page number"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      const pageNum = parseInt(e.currentTarget.value);
                      if (pageNum >= 1 && pageNum <= bookContent.total_pages) {
                        onPageClick(pageNum);
                        e.currentTarget.value = '';
                      }
                    }
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TableOfContents;
