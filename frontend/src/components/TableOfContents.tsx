import React, { useMemo, useState, useEffect } from 'react';
import { BookContent, Section } from '../reader/types';
import { getEngine } from '../reader/engine';

interface TableOfContentsProps {
  isOpen: boolean;
  onClose: () => void;
  bookContent: BookContent;
}

const TableOfContents: React.FC<TableOfContentsProps> = ({
  isOpen,
  onClose,
  bookContent,
}) => {
  const [goToPageInput, setGoToPageInput] = useState('');

  const sections = useMemo(() => {
    if (bookContent.sections && bookContent.sections.length > 0) {
      return bookContent.sections;
    }

    const fallbackSections: Section[] = [];
    bookContent.pages.forEach((page, idx) => {
      if (idx % 10 === 0) {
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

  const handleSectionClick = (section: Section) => {
    const engine = getEngine();
    if (engine) {
      // Prioritize blockId if available and valid, otherwise use pageNumber
      if (section.startBlockIndex !== undefined && section.startBlockIndex !== null) {
        const blockId = bookContent.pages[section.startPageNumber - 1]?.blocks[section.startBlockIndex]?.id;
        if (blockId) {
          engine.scrollToBlock(blockId, true);
        } else {
          engine.scrollToPage(section.startPageNumber, true);
        }
      } else {
        engine.scrollToPage(section.startPageNumber, true);
      }
    }
    onClose();
  };

  const handleGoToPage = () => {
    const pageNum = parseInt(goToPageInput);
    if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= bookContent.total_pages) {
      const engine = getEngine();
      if (engine) {
        engine.scrollToPage(pageNum, true);
      }
      setGoToPageInput('');
      onClose();
    } else {
      alert(`Please enter a valid page number between 1 and ${bookContent.total_pages}`);
    }
  };

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
          onClick={() => handleSectionClick(section)}
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

              {sections.map((section) => renderSectionItem(section))}

              <div className="reader-toc-divider" />
              <div className="reader-toc-quick-nav">
                <label className="reader-toc-label">Go to page:</label>
                <input
                  type="number"
                  className="reader-toc-input"
                  min="1"
                  max={bookContent.total_pages}
                  placeholder="Page number"
                  value={goToPageInput}
                  onChange={(e) => setGoToPageInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleGoToPage();
                    }
                  }}
                />
                <button onClick={handleGoToPage} className="reader-toc-go-btn">Go</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TableOfContents;
