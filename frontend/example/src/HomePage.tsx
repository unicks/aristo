import React from "react";
import { useNavigate } from "react-router-dom";
import "./style/App.css";
import "../../dist/style.css";

const features = [
  { icon: "📄", text: "בדיקת קבצי .tex או .pdf", bg: "linear-gradient(135deg, #f0e7ff 0%, #e0e7ff 100%)" },
  { icon: "🧑‍🏫", text: "מבוסס על דוגמאות בדיקה אמיתיות של מתרגלים", bg: "linear-gradient(135deg, #e0f7fa 0%, #e0e7ff 100%)" },
  { icon: "💬", text: "פלט: ציונים והערות ברורות לכל סעיף", bg: "linear-gradient(135deg, #fffbe7 0%, #e0e7ff 100%)" },
  { icon: "📝", text: "מייצר קובץ LaTeX מסכם של הערות", bg: "linear-gradient(135deg, #e7fff7 0%, #e0e7ff 100%)" },
  { icon: "⭐", text: "כולל תמצות לציון כולל והערה כללית", bg: "linear-gradient(135deg, #ffe7f7 0%, #e0e7ff 100%)" },
  { icon: "☁️", text: "שליפת תרגילים אוטומטית מ-Google Drive שיתופי", bg: "linear-gradient(135deg, #e7f0ff 0%, #e0e7ff 100%)" },
];

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100vw",
        fontFamily: 'Segoe UI',
        padding: 0,
        margin: 0,
        background: `linear-gradient(120deg, #f8fafc 0%, #e0e7ff 100%)`,
        position: "relative",
        overflowX: "hidden",
      }}
    >
      {/* Decorative SVG at the top */}
      <svg
        width="100%"
        height="120"
        viewBox="0 0 1440 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ position: "absolute", top: 0, left: 0, zIndex: 0 }}
      >
        <path
          d="M0,80 C360,160 1080,0 1440,80 L1440,0 L0,0 Z"
          fill="#6366f1"
          fillOpacity="0.10"
        />
      </svg>

      {/* Hero Section */}
      <section
        style={{
          width: "100%",
          background: "linear-gradient(90deg, #3b82f6 0%, #6366f1 100%)",
          color: "white",
          padding: "4.5rem 0 3.5rem 0",
          textAlign: "center",
          boxShadow: "0 8px 32px 0 rgba(99,102,241,0.13)",
          borderBottomLeftRadius: 48,
          borderBottomRightRadius: 48,
          position: "relative",
          zIndex: 1,
        }}
      >
        <div style={{ fontSize: "3.2rem", fontWeight: 900, letterSpacing: 1, marginBottom: 16, textShadow: "0 2px 16px #6366f1aa" }}>
          <span role="img" aria-label="books">📚</span> Aristo AI
        </div>
        <div style={{ fontSize: "1.7rem", fontWeight: 500, marginBottom: 22, textShadow: "0 1px 8px #6366f1aa" }}>
          מערכת חכמה לבדיקה אוטומטית של תרגילים מתמטיים
        </div>
        <div style={{ fontSize: "1.15rem", opacity: 0.95, marginBottom: 40, fontWeight: 400 }}>
          קבלו משוב מיידי, ציונים והערות – גם כשאין בודק אנושי זמין
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 20, flexWrap: 'wrap' }}>
          <button
            style={{
              padding: "1.2rem 3.2rem",
              fontSize: "1.35rem",
              background: "#fff",
              color: "#3b82f6",
              border: "none",
              borderRadius: 14,
              cursor: "pointer",
              fontWeight: 800,
              boxShadow: "0 4px 24px rgba(59,130,246,0.18)",
              transition: "background 0.2s, color 0.2s",
              letterSpacing: 0.5,
            }}
            onClick={() => navigate("/check")}
          >
            🚀 בדוק תרגילים עכשיו
          </button>
          <button
            style={{
              padding: "1.2rem 3.2rem",
              fontSize: "1.35rem",
              background: "linear-gradient(90deg, #10b981 0%, #22d3ee 100%)",
              color: "#fff",
              border: "none",
              borderRadius: 14,
              cursor: "pointer",
              fontWeight: 800,
              boxShadow: "0 4px 24px rgba(16,185,129,0.18)",
              transition: "background 0.2s, color 0.2s",
              letterSpacing: 0.5,
            }}
            onClick={() => navigate("/create")}
          >
            ✏️ צור תרגילים עכשיו
          </button>
        </div>
      </section>

      {/* Features Section */}
      <section
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          marginTop: "5.5rem",
          marginBottom: "5.5rem",
          padding: "0 1.5rem 2.5rem 1.5rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "2.5rem",
          zIndex: 2,
          position: "relative",
        }}
      >
        <div
          style={{
            background: "rgba(255,255,255,0.95)",
            borderRadius: 32,
            boxShadow: "0 12px 48px 0 rgba(99,102,241,0.10)",
            padding: "4rem 2.5rem 3.5rem 2.5rem",
            width: "100%",
            maxWidth: 820,
            textAlign: "center",
            marginTop: 0,
            border: "1.5px solid #e0e7ff",
          }}
        >
          <h2 style={{ color: "#1e293b", fontWeight: 800, fontSize: "2.3rem", marginBottom: 36, letterSpacing: 0.5 }}>
            למה Aristo?
          </h2>
          <p style={{ color: "#334155", fontSize: "1.18rem", marginBottom: 48, lineHeight: 1.8, fontWeight: 400 }}>
            בגלל מחסור חמור בכוח אדם, תרגילים רבים כיום כלל אינם נבדקים.<br />
            סטודנטים לא מקבלים פידבק, מה שפוגע בתהליך הלמידה ומקטין את המוטיבציה.<br />
            Aristo AI מספק פתרון אוטומטי, מדויק ויעיל – כך שכל סטודנט יקבל הערכה ומשוב על עבודתו.
          </p>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: 36,
              marginTop: 16,
            }}
          >
            {features.map((f, i) => (
              <div
                key={i}
                style={{
                  background: f.bg,
                  borderRadius: 20,
                  boxShadow: `0 2px 16px 0 ${f.bg.includes('#e0e7ff') ? '#e0e7ff88' : '#6366f188'}`,
                  padding: "2.2rem 1.2rem 1.7rem 1.2rem",
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  fontSize: '1.18rem',
                  color: '#334155',
                  fontWeight: 500,
                  minHeight: 140,
                  border: "1.5px solid #e0e7ff",
                  transition: "box-shadow 0.2s, transform 0.2s",
                  boxSizing: "border-box",
                }}
              >
                <span style={{ fontSize: '2.3rem', marginBottom: 14 }}>{f.icon}</span>
                {f.text}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Call to Action Section */}
      <section
        style={{
          background: "linear-gradient(90deg, #6366f1 0%, #3b82f6 100%)",
          color: "white",
          padding: "3.2rem 0 2.5rem 0",
          textAlign: "center",
          marginTop: 0,
          borderTopLeftRadius: 48,
          borderTopRightRadius: 48,
          boxShadow: "0 -8px 32px 0 rgba(99,102,241,0.10)",
        }}
      >
        <div style={{ fontSize: "1.7rem", fontWeight: 700, marginBottom: 28, letterSpacing: 0.5 }}>
          הצטרפו למהפכת הבדיקה האוטומטית!
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 20, flexWrap: 'wrap' }}>
          <button
            style={{
              padding: "1.2rem 3.2rem",
              fontSize: "1.35rem",
              background: "#fff",
              color: "#3b82f6",
              border: "none",
              borderRadius: 14,
              cursor: "pointer",
              fontWeight: 800,
              boxShadow: "0 4px 24px rgba(59,130,246,0.18)",
              transition: "background 0.2s, color 0.2s",
              letterSpacing: 0.5,
            }}
            onClick={() => navigate("/check")}
          >
            🚀 בדוק תרגילים עכשיו
          </button>
          <button
            style={{
              padding: "1.2rem 3.2rem",
              fontSize: "1.35rem",
              background: "linear-gradient(90deg, #10b981 0%, #22d3ee 100%)",
              color: "#fff",
              border: "none",
              borderRadius: 14,
              cursor: "pointer",
              fontWeight: 800,
              boxShadow: "0 4px 24px rgba(16,185,129,0.18)",
              transition: "background 0.2s, color 0.2s",
              letterSpacing: 0.5,
            }}
            onClick={() => navigate("/create")}
          >
            ✏️ צור תרגילים עכשיו
          </button>
        </div>
      </section>
    </div>
  );
};

export default HomePage; 