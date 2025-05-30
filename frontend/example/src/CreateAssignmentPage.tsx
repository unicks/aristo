import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PdfLoader } from "./react-pdf-highlighter";
import { Spinner } from "./Spinner";
import "./style/App.css";
import "../../dist/style.css";

export async function downloadFileFromServer(fileUrl: string, suggestedFilename?: string) {
  try {
    const response = await fetch(fileUrl);
    if (!response.ok) throw new Error("Download failed");

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = suggestedFilename || "downloaded_file.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();

    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Download error:", err);
    alert("שגיאה בהורדת הקובץ");
  }
}


const CreateAssignmentPage: React.FC = () => {
  const navigate = useNavigate();
  const [latex, setLatex] = useState("");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [questionsPreview, setQuestionsPreview] = useState<string | null>(null);
  const [downloadMethod, setDownloadMethod] = useState<string | null>(null);

  const handlePdfUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setPdfUrl(url);
    }
  };

  const handleTexUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setIsGenerating(true);
    setQuestionsPreview(null);
    setDownloadMethod(null);

    try {
      const res = await fetch("http://localhost:5000/compile-tex", {
        
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "שגיאה בהעלאת קובץ TeX");
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      setPdfUrl(url);
      // Optionally: setQuestionsPreview(null);
    } catch (err) {
      alert("שגיאה בהעלאת קובץ TeX");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownloadTex = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch("http://localhost:5000/generate-questions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt: latex }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "שגיאה בהורדת קובץ TeX");
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "generated_questions.tex";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("שגיאה בהורדת קובץ TeX");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #e0e7ff 0%, #f8fafc 100%)",
      fontFamily: 'Segoe UI',
      padding: 0,
      margin: 0,
    }}>
      <header style={{
        width: "100%",
        background: "#10b981",
        color: "white",
        padding: "2rem 0 1.5rem 0",
        boxShadow: "0 2px 12px rgba(16,185,129,0.08)",
        textAlign: "center",
      }}>
        <div style={{ fontSize: "2.2rem", fontWeight: 700, letterSpacing: 1 }}>
          ✏️ צור תרגילים חדשים
        </div>
        <div style={{ fontSize: "1.1rem", marginTop: 8, fontWeight: 400 }}>
        צור תרגילים חדשים 
        </div>
        <button
          style={{
            position: "absolute",
            left: 24,
            top: 24,
            padding: "0.7rem 2rem",
            fontSize: "1rem",
            background: "#6366f1",
            color: "white",
            border: "none",
            borderRadius: 8,
            cursor: "pointer",
            fontWeight: 600,
            boxShadow: "0 2px 8px rgba(99,102,241,0.13)",
            transition: "background 0.2s"
          }}
          onClick={() => navigate("/")}
        >
          חזרה לדף הבית
        </button>
      </header>
      <main style={{
        maxWidth: 700,
        margin: "0 auto",
        padding: "2.5rem 1.5rem 1.5rem 1.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "2.5rem",
      }}>
        <section style={{
          background: "white",
          borderRadius: 18,
          boxShadow: "0 2px 16px rgba(16,185,129,0.07)",
          padding: "2rem 2rem 1.5rem 2rem",
          textAlign: "right",
          direction: "rtl",
        }}>
          <h2 style={{ color: "#0ea5e9", fontWeight: 600, fontSize: "1.3rem", marginBottom: 12 }}>תאר את נושאי המטלה ואת רמת הקושי שלה</h2>
          <textarea
            value={latex}
            onChange={e => setLatex(e.target.value)}
            placeholder={" ניסוח גבולות בעזרת היינה תרגילים קשים\n פונקציות מורכבות בעזרת גזירה קלים\n משוואות דיפרנציאליות בעזרת משפט קיילי-המילטון\n וכדומה..."}
            style={{
              width: "100%",
              minHeight: 120,
              fontSize: "1.1rem",
              padding: 12,
              borderRadius: 8,
              border: "1px solid #cbd5e1",
              fontFamily: 'Consolas, monospace',
              marginBottom: 16,
              background: "#f8fafc"
            }}
          />
          <div style={{ marginBottom: 16 }}>
          </div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
            <button
              style={{
                padding: "0.8rem 2.2rem",
                fontSize: "1.1rem",
                background: "linear-gradient(90deg, #10b981 0%, #22d3ee 100%)",
                color: "white",
                border: "none",
                borderRadius: 8,
                cursor: isGenerating ? "not-allowed" : "pointer",
                fontWeight: 600,
                boxShadow: "0 2px 8px rgba(16,185,129,0.13)",
                transition: "background 0.2s"
              }}
              disabled={isGenerating || !latex.trim()}
              onClick={handleDownloadTex}
            >
              {isGenerating ? "יוצר קובץ TeX..." : "צור קובץ TeX להורדה"}
            </button>
          </div>
        </section>
        <section style={{
          background: "#f1f5f9",
          borderRadius: 16,
          padding: "1.5rem 2rem",
          boxShadow: "0 1px 6px rgba(16,185,129,0.04)",
          textAlign: "center",
        }}>
          <h3 style={{ color: "#10b981", fontWeight: 600, fontSize: "1.1rem", marginBottom: 10 }}>תצוגה מקדימה / פלט</h3>
          {/* Questions Preview */}
          {questionsPreview && (
            <div style={{
              marginTop: 24,
              background: "#fffbe7",
              border: "1px solid #facc15",
              borderRadius: 10,
              padding: 18,
              color: "#92400e",
              fontFamily: 'Heebo, sans-serif',
              fontSize: "1.13rem",
              textAlign: "right",
              direction: "rtl",
              boxShadow: "0 2px 8px rgba(250,204,21,0.07)"
            }}>
              <div style={{ fontWeight: 700, marginBottom: 8, color: "#ca8a04" }}>
                תצוגה מקדימה של השאלות שנוצרו:
              </div>
              <pre style={{
                background: "none",
                border: "none",
                padding: 0,
                margin: 0,
                fontFamily: 'Consolas, monospace',
                fontSize: "1.05rem",
                whiteSpace: "pre-wrap"
              }}>{questionsPreview}</pre>
            </div>
          )}
          {/* Download method message */}
          {downloadMethod === 'saveFilePicker' && (
            <div style={{ marginTop: 18, color: '#10b981', fontWeight: 600 }}>
              בחרת ידנית היכן לשמור את הקובץ (File Save Dialog)
            </div>
          )}
          {downloadMethod === 'newTab' && (
            <div style={{ marginTop: 18, color: '#f59e42', fontWeight: 600 }}>
              הקובץ נפתח בלשונית חדשה. אנא לחץ על סמל ההורדה או השתמש ב-"שמור בשם..." כדי לבחור היכן לשמור את הקובץ.
            </div>
          )}
          {/* Always show PDF preview if available */}
          {/*
          {pdfUrl && (
            <div style={{ marginTop: 32, borderRadius: 10, overflow: 'hidden', boxShadow: '0 2px 8px rgba(16,185,129,0.07)' }}>
              <iframe
                src={pdfUrl}
                title="PDF Preview"
                width="100%"
                height="500px"
                style={{ border: "none", borderRadius: 10 }}
              />
            </div>
          )}
          */}
        </section>
      </main>
    </div>
  );
};

export default CreateAssignmentPage; 