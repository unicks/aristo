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
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [courses, setCourses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [isCheckingFiles, setIsCheckingFiles] = useState<boolean>(false);

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

  const handleBase64Upload = (base64Files: Array<{ content_base64: string; filename: string }>) => {
  const newPdfs = base64Files.map(({ content_base64, filename }) => {
    // Decode base64 to binary
    const byteCharacters = atob(content_base64);
    const byteArrays = new Uint8Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteArrays[i] = byteCharacters.charCodeAt(i);
    }

    // Create Blob and File
    const pdfBlob = new Blob([byteArrays], { type: "application/pdf" });
    const fileUrl = URL.createObjectURL(pdfBlob);
    blobUrlsRef.current.add(fileUrl); // Track blob URL for cleanup

    return {
      url: fileUrl,
      name: filename,
      highlights: []
    };
  });

  const currentLength = uploadedPdfs.length;
  setUploadedPdfs(prev => [...prev, ...newPdfs]);

  if (currentLength === 0 && newPdfs.length > 0) {
    setCurrentPdfIndex(0);
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
  
  useEffect(() => {
    const fetchAssignments = async () => {
      try {
        const res = await fetch("http://localhost:5000/courses");
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        const data = await res.json();
        setCourses(data.courses); 
      } catch (error) {
        console.error("Failed to fetch assignments:", error);
      }
    };
    fetchAssignments();
  }, []);

  useEffect(() => {
  if (!selectedCourseId) return; // לא לרוץ אם אין קורס נבחר

  const fetchAssignments = async () => {
    try {
      const res = await fetch(`http://localhost:5000/assignments?courseid=${selectedCourseId}`);
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      setAssignments(data.assignments); 
    } catch (error) {
      console.error("Failed to fetch assignments:", error);
    }
  };

  fetchAssignments();
}, [selectedCourseId]);

  return (
    <div className="App" style={{ display: "flex", height: "100vh" }}>
      <Sidebar
        highlights={highlights}
        resetHighlights={resetHighlights}
      >
        <div style={{ padding: "1rem" }}>
          <h4>Choose assignment you want to check</h4>
            <div style={{ marginBottom: "1.5rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontWeight: 600, fontSize: "1rem" }}>Choose Course:</span>
              <select
                value={selectedCourseId ?? ""}
                onChange={(e) => setSelectedCourseId(Number(e.target.value))}
                style={{
                padding: "0.4rem 0.8rem",
                borderRadius: "6px",
                border: "1px solid #ccc",
                fontSize: "1rem",
                minWidth: "160px",
                background: "#fafbfc"
                }}
              >
                <option value="" disabled>
                {courses.length === 0 ? "Loading..." : "Select a course"}
                </option>
                {Array.isArray(courses) && courses.length > 0 &&
                courses.map((course: any) => (
                  <option key={course.id} value={course.id}>
                  {course.fullname}
                  </option>
                ))}
              </select>
              </label>
            </div>
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontWeight: 600, fontSize: "1rem" }}>Choose Assignment:</span>
              <select
                disabled={!selectedCourseId}
                style={{
                padding: "0.4rem 0.8rem",
                borderRadius: "6px",
                border: "1px solid #ccc",
                fontSize: "1rem",
                minWidth: "160px",
                background: !selectedCourseId ? "#f0f0f0" : "#fafbfc"
                }}
              >
                <option value="" disabled>
                {!selectedCourseId
                  ? "Select a course first"
                  : assignments.length === 0
                  ? "Loading..."
                  : "Select an assignment"}
                </option>
                {Array.isArray(assignments) && assignments.length > 0 &&
                assignments.map((assignment: any) => (
                  <option key={assignment.id} value={assignment.id}>
                  {assignment.name}
                  </option>
                ))}
              </select>
              </label>
            </div>
            </div>
            <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
              <button
                disabled={!selectedCourseId || assignments.length === 0 || isCheckingFiles}
                style={{
                  padding: "0.6rem 1.2rem",
                  borderRadius: "6px",
                  border: "none",
                  background: isCheckingFiles ? "#ccc" : (!selectedCourseId || assignments.length === 0 ? "#aab8c2" : "#1976d2"),
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: "1rem",
                  cursor: !selectedCourseId || assignments.length === 0 || isCheckingFiles ? "not-allowed" : "pointer",
                  marginTop: "1rem"
                }}
                onClick={async () => {
                  const assignmentSelect = document.querySelector<HTMLSelectElement>('select[disabled=""]') || document.querySelectorAll('select')[1];
                  const assignmentId = (assignmentSelect as HTMLSelectElement)?.value;
                  if (!assignmentId) {
                    alert("Please select an assignment.");
                    return;
                  }
                  setIsCheckingFiles(true);
                  try {
                    // Example API call - replace URL and method as needed
                    const res = await fetch("http://localhost:5000/choose", {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                      },
                      body: JSON.stringify({
                        amount: 2,
                        exercise_id: assignmentId,
                      }),
                    });
                    if (!res.ok) throw new Error("API call failed");
                    const data = await res.json();
                    const files = data.files;
                    handleBase64Upload(files);
                  } catch (err) {
                    alert("API call failed: " + err);
                  } finally {
                    setIsCheckingFiles(false);
                  }
                }}
              >{isCheckingFiles ? "Checking..." : "Check Files"} 
              </button>
              <button
                  disabled={!selectedCourseId || assignments.length === 0 || isCheckingFiles}
                  style={{
                  padding: "0.6rem 1.2rem",
                  borderRadius: "6px",
                  border: "none",
                  background: isCheckingFiles ? "#ccc" : (!selectedCourseId || assignments.length === 0 ? "#aab8c2" : "#1976d2"),
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: "1rem",
                  cursor: !selectedCourseId || assignments.length === 0 || isCheckingFiles ? "not-allowed" : "pointer",
                  marginTop: "1rem"
                }}>
                Grade All
              </button>
            </div>
              {/* PDF navigation buttons */}
              <div style={{ display: "flex", gap: "1rem", marginTop: "2rem", justifyContent: "center" }}>
                <button
                  onClick={() => navigateToPdf('prev')}
                  disabled={currentPdfIndex <= 0}
                  style={{
                    padding: "0.5rem 1rem",
                    borderRadius: "4px",
                    border: "1px solid #ccc",
                    background: currentPdfIndex <= 0 ? "#eee" : "#fff",
                    color: "#333",
                    cursor: currentPdfIndex <= 0 ? "not-allowed" : "pointer",
                    fontWeight: 600
                  }}
                >
                  Previous
                </button>
                <span style={{ alignSelf: "center", fontWeight: 500 }}>
                  {uploadedPdfs.length > 0
                    ? `PDF ${currentPdfIndex + 1} of ${uploadedPdfs.length}`
                    : "No PDFs"}
                </span>
                <button
                  onClick={() => navigateToPdf('next')}
                  disabled={currentPdfIndex >= uploadedPdfs.length - 1}
                  style={{
                    padding: "0.5rem 1rem",
                    borderRadius: "4px",
                    border: "1px solid #ccc",
                    background: currentPdfIndex >= uploadedPdfs.length - 1 ? "#eee" : "#fff",
                    color: "#333",
                    cursor: currentPdfIndex >= uploadedPdfs.length - 1 ? "not-allowed" : "pointer",
                    fontWeight: 600
                  }}
                >
                  Next
                </button>
              </div>
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
