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
import logoImg from "./assets/logo.png";

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
          <h4 style={{ 
            marginBottom: "0.75rem",
            color: "#2c3e50",
            fontSize: "1rem",
            fontWeight: "600",
          }}>
            Upload PDF Files
          </h4>
          <div style={{ position: "relative", marginBottom: "0.5rem" }}>
            <input
              type="file"
              accept=".pdf"
              multiple
              onChange={handleFileUpload}
              style={{
                position: "absolute",
                opacity: 0,
                width: "100%",
                height: "100%",
                cursor: "pointer",
              }}
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              style={{
                display: "block",
                width: "100%",
                padding: "0.6rem 0.5rem",
                backgroundColor: "#007bff",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "0.8rem",
                fontWeight: "500",
                textAlign: "center",
                transition: "all 0.15s ease",
                boxShadow: "0 1px 3px rgba(0, 123, 255, 0.2)",
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.backgroundColor = "#0056b3";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.backgroundColor = "#007bff";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              📁 Choose PDF Files
            </label>
          </div>
          <p style={{ 
            fontSize: "0.75rem", 
            color: "#6c757d", 
            margin: "0 0 1rem 0",
            textAlign: "center",
          }}>
            You can select multiple PDF files at once
          </p>
          
          {uploadedPdfs.length > 0 && (
            <div style={{ marginBottom: "1rem" }}>
              <h4 style={{ 
                marginBottom: "0.75rem",
                color: "#2c3e50",
                fontSize: "1rem",
                fontWeight: "600",
              }}>
                PDF Navigation ({uploadedPdfs.length} files)
              </h4>
              <div style={{ 
                display: "flex", 
                alignItems: "center", 
                gap: "0.5rem",
                marginBottom: "0.75rem"
              }}>
                <button
                  onClick={() => navigateToPdf('prev')}
                  disabled={currentPdfIndex === 0}
                  style={{
                    padding: "0.4rem 0.6rem",
                    backgroundColor: currentPdfIndex === 0 ? "#f8f9fa" : "#007bff",
                    color: currentPdfIndex === 0 ? "#adb5bd" : "white",
                    border: currentPdfIndex === 0 ? "1px solid #dee2e6" : "none",
                    borderRadius: "6px",
                    cursor: currentPdfIndex === 0 ? "not-allowed" : "pointer",
                    fontSize: "0.9rem",
                    fontWeight: "500",
                    transition: "all 0.15s ease",
                  }}
                >
                  ←
                </button>
                <span style={{ 
                  fontSize: "0.85rem", 
                  flex: 1, 
                  textAlign: "center",
                  fontWeight: "500",
                  color: "#495057",
                }}>
                  {currentPdfIndex + 1} of {uploadedPdfs.length}
                </span>
                <button
                  onClick={() => navigateToPdf('next')}
                  disabled={currentPdfIndex === uploadedPdfs.length - 1}
                  style={{
                    padding: "0.4rem 0.6rem",
                    backgroundColor: currentPdfIndex === uploadedPdfs.length - 1 ? "#f8f9fa" : "#007bff",
                    color: currentPdfIndex === uploadedPdfs.length - 1 ? "#adb5bd" : "white",
                    border: currentPdfIndex === uploadedPdfs.length - 1 ? "1px solid #dee2e6" : "none",
                    borderRadius: "6px",
                    cursor: currentPdfIndex === uploadedPdfs.length - 1 ? "not-allowed" : "pointer",
                    fontSize: "0.9rem",
                    fontWeight: "500",
                    transition: "all 0.15s ease",
                  }}
                >
                  →
                </button>
              </div>
              {currentPdf && (
                <div style={{ 
                  fontSize: "0.75rem", 
                  color: "#6c757d",
                  padding: "0.5rem",
                  backgroundColor: "#f8f9fa",
                  borderRadius: "4px",
                  marginBottom: "0.5rem",
                }}>
                  <div style={{ fontWeight: "500", marginBottom: "0.2rem" }}>
                    {currentPdf.name}
                  </div>
                  <div>
                    {currentPdf.highlights.length} comments
                  </div>
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
                padding: "0.6rem",
                backgroundColor: "#28a745",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: "500",
                transition: "all 0.15s ease",
                marginBottom: "0.5rem",
              }}
            >
              📥 Export Comments
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
              backgroundColor: "#f8f9fa",
              color: "#495057",
              padding: "2rem",
              textAlign: "center",
            }}
          >
            <img 
              src={logoImg} 
              alt="PDF Highlighter Logo" 
              style={{
                width: "120px",
                height: "120px",
                marginBottom: "2rem",
                borderRadius: "16px",
                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
              }}
            />
            <h1 style={{ 
              marginBottom: "1rem", 
              fontSize: "2.5rem",
              fontWeight: "700",
              color: "#2c3e50",
              lineHeight: "1.2",
            }}>
              PDF Highlighter
            </h1>
            <p style={{
              fontSize: "1.1rem",
              color: "#6c757d",
              maxWidth: "500px",
              lineHeight: "1.6",
              marginBottom: "0.5rem",
            }}>
              {uploadedPdfs.length === 0 
                ? "Upload PDF files and start highlighting important content with smart annotations and comments."
                : "Select a PDF from the sidebar to begin highlighting and annotating."
              }
            </p>
            <p style={{
              fontSize: "0.9rem",
              color: "#868e96",
              fontStyle: "italic",
            }}>
              {uploadedPdfs.length === 0 
                ? "Use the sidebar to upload your PDF files and get started"
                : "Navigate between your uploaded PDFs using the sidebar controls"
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
