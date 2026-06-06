import React, { useState } from 'react';
import { ReaderView } from './components/ReaderView';
import { BookContent } from './reader/types';

// Mock book content for demonstration
const mockBookContent: BookContent = {
  book_id: 'mock-book-1',
  total_pages: 5,
  pages: [
    {
      page_number: 1,
      blocks: [
        { id: 'p1-b1', type: 'text', content: 'This is the first paragraph of page 1. It contains some introductory text to demonstrate the FlexiRead application. We will test various features like scrolling, theme changes, and font adjustments.' },
        { id: 'p1-b2', type: 'image', content: 'https://via.placeholder.com/400x200?text=Image+1' },
        { id: 'p1-b3', type: 'text', content: 'Another paragraph on page 1. This one is a bit longer to show how text wraps and fills the available space. The reader should handle different text lengths gracefully.' },
      ],
      is_ocr: false,
    },
    {
      page_number: 2,
      blocks: [
        { id: 'p2-b1', type: 'text', content: 'Page 2 starts here. This content is meant to simulate the continuation of a book. We can add more complex elements as needed.' },
        { id: 'p2-b2', type: 'formula', content: 'E=mc^2' },
        { id: 'p2-b3', type: 'text', content: 'A formula block is rendered above. This demonstrates the integration of mathematical expressions within the reader. The engine should correctly display these using MathJax or KaTeX.' },
      ],
      is_ocr: false,
    },
    {
      page_number: 3,
      blocks: [
        { id: 'p3-b1', type: 'text', content: 'This is page 3. The virtual scrolling mechanism should ensure that only a few pages around the current view are rendered in the DOM to optimize performance and memory usage.' },
        { id: 'p3-b2', type: 'question', content: 'What is the primary benefit of using a virtualized scrolling approach in a document reader?' },
        { id: 'p3-b3', type: 'text', content: 'The question block is an example of a custom content type. It allows for interactive elements or specific formatting for certain types of content within the document.' },
      ],
      is_ocr: false,
    },
    {
      page_number: 4,
      blocks: [
        { id: 'p4-b1', type: 'text', content: 'Page 4 content. We are getting closer to the end of our mock book. This page will contain more text to fill up space.' },
        { id: 'p4-b2', type: 'image', content: 'https://via.placeholder.com/600x300?text=Image+2' },
        { id: 'p4-b3', type: 'text', content: 'Another image is displayed here. The image scaling preference should affect how this image is rendered within the reader view. Users can adjust it from the settings panel.' },
      ],
      is_ocr: false,
    },
    {
      page_number: 5,
      blocks: [
        { id: 'p5-b1', type: 'text', content: 'Finally, page 5. This is the last page of our demonstration book. We hope all features are working as expected.' },
        { id: 'p5-b2', type: 'formula', content: '\\sum_{n=1}^{\\infty} \\frac{1}{n^2} = \\frac{\\pi^2}{6}' },
        { id: 'p5-b3', type: 'text', content: 'End of the book. Thank you for testing FlexiRead!' },
      ],
      is_ocr: false,
    },
  ],
  sections: [
    { id: 'sec-1', title: 'Introduction', startPageNumber: 1, startBlockIndex: 0, level: 1 },
    { id: 'sec-2', title: 'Core Concepts', startPageNumber: 2, startBlockIndex: 0, level: 1 },
    { id: 'sec-3', title: 'Advanced Features', startPageNumber: 3, startBlockIndex: 0, level: 1 },
    { id: 'sec-4', title: 'Conclusion', startPageNumber: 5, startBlockIndex: 0, level: 1 },
  ],
  metadata: {
    title: 'FlexiRead Demo Book',
    author: 'Manus AI',
    total_words: 2500,
    language: 'en',
  },
};

function App() {
  const [progress, setProgress] = useState({ pageNumber: 1, blockIndex: 0 });

  const handleProgressChange = (pageNumber: number, blockIndex: number) => {
    setProgress({ pageNumber, blockIndex });
  };

  return (
    <div className="App">
      <ReaderView
        bookId={mockBookContent.book_id}
        bookContent={mockBookContent}
        onProgressChange={handleProgressChange}
      />
      <div style={{ position: 'fixed', bottom: 0, left: 0, background: 'rgba(0,0,0,0.7)', color: 'white', padding: '5px 10px', fontSize: '0.8em' }}>
        Progress: Page {progress.pageNumber}, Block {progress.blockIndex}
      </div>
    </div>
  );
}

export default App;
