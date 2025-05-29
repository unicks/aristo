import React, { useState, useEffect, useCallback, useRef } from "react";
import { PDFDocument, rgb, StandardFonts } from "pdf-lib";

import {
  AreaHighlight,
  Highlight,
  PdfHighlighter,
  PdfLoader,
  Popup,
} from "./react-pdf-highlighter";
import type {
  Content,
  IHighlight,
  NewHighlight,
  ScaledPosition,
} from "./react-pdf-highlighter";

import { Sidebar } from "./Sidebar";
import { Spinner } from "./Spinner";
import { Tip } from "./Tip";
import { testHighlights as _testHighlights } from "./test-highlights";

import "./style/App.css";
import "../../dist/style.css";

const testHighlights: Record<string, Array<IHighlight>> = _testHighlights;

const getNextId = () => String(Math.random()).slice(2);

const parseIdFromHash = () =>
  document.location.hash.slice("#highlight-".length);

const resetHash = () => {
  document.location.hash = "";
};

const HighlightPopup = ({
  comment,
}: {
  comment: { text: string; emoji: string };
}) =>
  comment.text ? (
    <div className="Highlight__popup">
      {comment.emoji} {comment.text}
    </div>
  ) : null;

export function App() {
  const searchParams = new URLSearchParams(document.location.search);
  const initialUrl = searchParams.get("url") || "";

  const [uploadedPdfs, setUploadedPdfs] = useState<Array<{
    url: string;
    name: string;
    highlights: Array<IHighlight>;
  }>>([]);
  const [currentPdfIndex, setCurrentPdfIndex] = useState<number>(0);
  
  // Keep track of blob URLs for cleanup
  const blobUrlsRef = useRef<Set<string>>(new Set());

  // Get current PDF data
  const currentPdf = uploadedPdfs[currentPdfIndex] || null;
  const url = currentPdf?.url || (uploadedPdfs.length === 0 ? initialUrl : "");
  const highlights = currentPdf?.highlights || [];

  // Debug logging
  console.log('=== PDF STATE DEBUG ===');
  console.log('Current PDF Index:', currentPdfIndex);
  console.log('Total PDFs:', uploadedPdfs.length);
  console.log('Current PDF:', currentPdf ? { name: currentPdf.name, highlightsCount: currentPdf.highlights.length } : 'None');
  console.log('Current URL:', url ? `${url.substring(0, 30)}...` : 'No URL');
  console.log('All PDFs:', uploadedPdfs.map((pdf, index) => ({ 
    index, 
    name: pdf.name, 
    highlightsCount: pdf.highlights.length,
    url: pdf.url.substring(0, 30) + '...'
  })));
  console.log('========================');

  const resetHighlights = () => {
    if (currentPdf) {
      setUploadedPdfs(prev => prev.map((pdf, index) => 
        index === currentPdfIndex 
          ? { ...pdf, highlights: [] }
          : pdf
      ));
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      const newPdfs = Array.from(files).map(file => {
        const fileUrl = URL.createObjectURL(file);
        blobUrlsRef.current.add(fileUrl); // Track the URL for cleanup
        return {
          url: fileUrl,
          name: file.name,
          highlights: []
        };
      });
      
      const currentLength = uploadedPdfs.length;
      setUploadedPdfs(prev => [...prev, ...newPdfs]);
      
      // If this is the first upload, switch to the first new PDF
      if (currentLength === 0) {
        setCurrentPdfIndex(0);
      }
      
      // Clear the input so the same files can be uploaded again if needed
      event.target.value = '';
    }
  };

  const navigateToPdf = (direction: 'prev' | 'next') => {
    const oldIndex = currentPdfIndex;
    let newIndex = oldIndex;
    
    if (direction === 'prev' && currentPdfIndex > 0) {
      newIndex = currentPdfIndex - 1;
    } else if (direction === 'next' && currentPdfIndex < uploadedPdfs.length - 1) {
      newIndex = currentPdfIndex + 1;
    }
    
    if (newIndex !== oldIndex) {
      console.log(`Navigating from PDF ${oldIndex} (${uploadedPdfs[oldIndex]?.name}) to PDF ${newIndex} (${uploadedPdfs[newIndex]?.name})`);
      setCurrentPdfIndex(newIndex);
    }
  };

  const setHighlights = (newHighlights: Array<IHighlight>) => {
    if (currentPdf) {
      setUploadedPdfs(prev => prev.map((pdf, index) => 
        index === currentPdfIndex 
          ? { ...pdf, highlights: newHighlights }
          : pdf
      ));
    }
  };

  // Cleanup blob URLs only when component unmounts
  useEffect(() => {
    return () => {
      // Only cleanup on component unmount
      blobUrlsRef.current.forEach(url => {
        URL.revokeObjectURL(url);
      });
      blobUrlsRef.current.clear();
    };
  }, []); // Empty dependency array - only run on mount/unmount

  const scrollViewerTo = useRef((highlight: IHighlight) => {});

  const scrollToHighlightFromHash = useCallback(() => {
    const highlight = getHighlightById(parseIdFromHash());
    if (highlight) {
      scrollViewerTo.current(highlight);
    }
  }, []);

  useEffect(() => {
    window.addEventListener("hashchange", scrollToHighlightFromHash, false);
    return () => {
      window.removeEventListener(
        "hashchange",
        scrollToHighlightFromHash,
        false,
      );
    };
  }, [scrollToHighlightFromHash]);

  const getHighlightById = (id: string) => {
    return highlights.find((highlight) => highlight.id === id);
  };

  const addHighlight = (highlight: NewHighlight) => {
    console.log("Saving highlight", highlight);
    const newHighlight = { ...highlight, id: getNextId() };
    if (currentPdf) {
      setUploadedPdfs(prev => prev.map((pdf, index) => 
        index === currentPdfIndex 
          ? { ...pdf, highlights: [newHighlight, ...pdf.highlights] }
          : pdf
      ));
    }
  };

  const updateHighlight = (
    highlightId: string,
    position: Partial<ScaledPosition>,
    content: Partial<Content>,
  ) => {
    console.log("Updating highlight", highlightId, position, content);
    if (currentPdf) {
      setUploadedPdfs(prev => prev.map((pdf, index) => 
        index === currentPdfIndex 
          ? { 
              ...pdf, 
              highlights: pdf.highlights.map((h) => {
                const {
                  id,
                  position: originalPosition,
                  content: originalContent,
                  ...rest
                } = h;
                return id === highlightId
                  ? {
                      id,
                      position: { ...originalPosition, ...position },
                      content: { ...originalContent, ...content },
                      ...rest,
                    }
                  : h;
              })
            }
          : pdf
      ));
    }
  };

  const downloadAnnotatedPdf = async () => {
    try {
      console.log('=== EXPORTING ALL COMMENTS ===');
      
      // Export each PDF separately
      for (let i = 0; i < uploadedPdfs.length; i++) {
        const pdf = uploadedPdfs[i];
        
        console.log(`\nExporting ${pdf.name}:`);
        
        // Create simplified JSON structure with question per comment
        const commentsData = pdf.highlights.map((highlight, index) => ({
          question: (highlight.comment as any)?.question || "Unspecified",
          context: highlight.content.text || '',
          comment: (highlight.comment as any)?.text || ''
        }));
        
        // Print to console for verification
        pdf.highlights.forEach((highlight, index) => {
          console.log(`\n--- Comment ${index + 1} ---`);
          console.log('Question:', (highlight.comment as any)?.question || 'Unspecified');
          console.log('Context (highlighted text):', highlight.content.text || 'No text content');
          console.log('Comment:', (highlight.comment as any)?.text || 'No comment');
          console.log('---');
        });
        
        if (commentsData.length > 0) {
          // Create and download JSON file for this PDF
          const jsonData = {
            fileName: pdf.name,
            totalComments: pdf.highlights.length,
            comments: commentsData
          };
          
          const jsonString = JSON.stringify(jsonData, null, 2);
          const blob = new Blob([jsonString], { type: 'application/json' });
          const downloadUrl = URL.createObjectURL(blob);
          
          // Create and click download link
          const link = document.createElement('a');
          link.href = downloadUrl;
          const safeName = pdf.name.replace(/\.pdf$/i, '').replace(/[^a-z0-9]/gi, '-');
          link.download = `comments-${safeName}-${new Date().toISOString().split('T')[0]}.json`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          
          // Clean up
          URL.revokeObjectURL(downloadUrl);
          
          // Small delay between downloads
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
      
      console.log(`\nAll comments exported successfully!`);
      console.log('=== END EXPORT ===');
      
    } catch (error) {
      console.error('Error extracting comments:', error);
    }
  };

  return (
    <div className="App" style={{ display: "flex", height: "100vh" }}>
      <Sidebar
        highlights={highlights}
        resetHighlights={resetHighlights}
      >
        <div style={{ padding: "1rem" }}>
          <h4>Upload PDF Files</h4>
          <input
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFileUpload}
            style={{ marginBottom: "1rem" }}
          />
          <p style={{ fontSize: "0.8rem", color: "#666", marginBottom: "1rem" }}>
            You can select multiple PDF files at once
          </p>
          
          {uploadedPdfs.length > 0 && (
            <div style={{ marginBottom: "1rem" }}>
              <h4>PDF Navigation ({uploadedPdfs.length} files)</h4>
              <div style={{ 
                display: "flex", 
                alignItems: "center", 
                gap: "0.5rem",
                marginBottom: "0.5rem"
              }}>
                <button
                  onClick={() => navigateToPdf('prev')}
                  disabled={currentPdfIndex === 0}
                  style={{
                    padding: "0.25rem 0.5rem",
                    backgroundColor: currentPdfIndex === 0 ? "#ccc" : "#007bff",
                    color: "white",
                    border: "none",
                    borderRadius: "3px",
                    cursor: currentPdfIndex === 0 ? "not-allowed" : "pointer",
                  }}
                >
                  ←
                </button>
                <span style={{ 
                  fontSize: "0.9rem", 
                  flex: 1, 
                  textAlign: "center",
                  fontWeight: "bold"
                }}>
                  {currentPdfIndex + 1} of {uploadedPdfs.length}
                </span>
                <button
                  onClick={() => navigateToPdf('next')}
                  disabled={currentPdfIndex === uploadedPdfs.length - 1}
                  style={{
                    padding: "0.25rem 0.5rem",
                    backgroundColor: currentPdfIndex === uploadedPdfs.length - 1 ? "#ccc" : "#007bff",
                    color: "white",
                    border: "none",
                    borderRadius: "3px",
                    cursor: currentPdfIndex === uploadedPdfs.length - 1 ? "not-allowed" : "pointer",
                  }}
                >
                  →
                </button>
              </div>
              {currentPdf && (
                <div style={{ 
                  fontSize: "0.8rem", 
                  color: "#666",
                  marginBottom: "0.5rem",
                  wordBreak: "break-word"
                }}>
                  Current: {currentPdf.name}
                  <br />
                  Comments: {currentPdf.highlights.length}
                </div>
              )}
            </div>
          )}
          
          {uploadedPdfs.some(pdf => pdf.highlights.length > 0) && (
            <button
              type="button"
              onClick={downloadAnnotatedPdf}
              style={{
                display: "block",
                width: "100%",
                padding: "0.5rem",
                backgroundColor: "#28a745",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                marginBottom: "0.5rem",
              }}
            >
              Export All Comments
            </button>
          )}
        </div>
      </Sidebar>
      <div
        style={{
          height: "100vh",
          width: "75vw",
          position: "relative",
        }}
      >
        {url ? (
          <PdfLoader 
            key={`pdf-${currentPdfIndex}-${currentPdf?.name}`}
            url={url} 
            beforeLoad={<Spinner />}
          >
            {(pdfDocument) => (
              <PdfHighlighter
                pdfDocument={pdfDocument}
                enableAreaSelection={(event) => event.altKey}
                onScrollChange={resetHash}
                scrollRef={(scrollTo) => {
                  scrollViewerTo.current = scrollTo;
                  scrollToHighlightFromHash();
                }}
                onSelectionFinished={(
                  position,
                  content,
                  hideTipAndSelection,
                  transformSelection,
                ) => (
                  <Tip
                    onOpen={transformSelection}
                    onConfirm={(comment) => {
                      console.log('Adding highlight to PDF:', currentPdf?.name);
                      addHighlight({ content, position, comment });
                      hideTipAndSelection();
                    }}
                  />
                )}
                highlightTransform={(
                  highlight,
                  index,
                  setTip,
                  hideTip,
                  viewportToScaled,
                  screenshot,
                  isScrolledTo,
                ) => {
                  const isTextHighlight = !highlight.content?.image;

                  const component = isTextHighlight ? (
                    <Highlight
                      isScrolledTo={isScrolledTo}
                      position={highlight.position}
                      comment={highlight.comment}
                    />
                  ) : (
                    <AreaHighlight
                      isScrolledTo={isScrolledTo}
                      highlight={highlight}
                      onChange={(boundingRect) => {
                        updateHighlight(
                          highlight.id,
                          { boundingRect: viewportToScaled(boundingRect) },
                          { image: screenshot(boundingRect) },
                        );
                      }}
                    />
                  );

                  return (
                    <Popup
                      popupContent={<HighlightPopup {...highlight} />}
                      onMouseOver={(popupContent) =>
                        setTip(highlight, (highlight) => popupContent)
                      }
                      onMouseOut={hideTip}
                      key={index}
                    >
                      {component}
                    </Popup>
                  );
                }}
                highlights={highlights}
              />
            )}
          </PdfLoader>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              flexDirection: "column",
              backgroundColor: "#f5f5f5",
              color: "#666",
            }}
          >
            <h2 style={{ marginBottom: "1rem" }}>
              {uploadedPdfs.length === 0 ? "No PDFs Uploaded" : "No PDF Selected"}
            </h2>
            <p>
              {uploadedPdfs.length === 0 
                ? "Please upload PDF files using the sidebar to get started."
                : "Use the navigation arrows in the sidebar to select a PDF."
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
