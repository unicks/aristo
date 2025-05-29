<!DOCTYPE html>
<html lang="he">

<body>

<h1 align="center">📚 Aristo AI - מערכת לבדיקה אוטומטית של תרגילים</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue?style=flat-square" alt="Python 3.10">
  <img src="https://img.shields.io/badge/Flask-API-green?style=flat-square" alt="Flask API">
  <img src="https://img.shields.io/badge/Gemini-AI%20grading-ff69b4?style=flat-square" alt="Gemini">
  <img src="https://img.shields.io/badge/Google%20Drive-Integration-yellow?style=flat-square" alt="Google Drive">
</p>

<p align="center">
  <strong>מערכת חכמה לבדיקה אוטומטית של תרגילים מתמטיים בקובצי LaTeX או PDF.</strong><br>
  מבוסס על Google Gemini + דוגמאות בדיקה אמיתיות של מתרגלים.
</p>

<hr>

<h2>🧠 למה בכלל?</h2>

<p>
בגלל מחסור חמור בכוח אדם, תרגילים רבים כיום כלל אינם נבדקים. <br>
סטודנטים לא מקבלים פידבק, מה שפוגע בתהליך הלמידה ומקטין את המוטיבציה.<br><br>

Aristo AI מציע פתרון פשוט ויעיל: מערכת אוטומטית שמספקת משוב מדויק, מבוסס על דגימת בדיקות ידניות שנעשו ע"י מתרגלים.
האוניברסיטה יכולה לשלב את המערכת כדי להבטיח שכל סטודנט יקבל הערכה על עבודתו, גם כשאין בודק אנושי זמין.
</p>

<h2>🚀 תכונות עיקריות</h2>

<ul>
  <li>✅ קלט: קובץ <code>.tex</code> או <code>.pdf</code> של פתרון תרגיל</li>
  <li>✅ מבוסס על קונטקסט בדיקה אמיתי שנדגם ממתרגל</li>
  <li>✅ פלט: JSON של ציונים והערות ברורות לכל סעיף</li>
  <li>✅ מייצר קובץ LaTeX מסכם של הערות</li>
  <li>✅ כולל תמצות לציון כולל והערה כללית</li>
  <li>✅ אפשרות לשלוף תרגילים אוטומטית מתוך Google Drive שיתופי</li>
</ul>

<h2>📁 מבנה הפרויקט</h2>

<pre>
backend/
├── app.py                 # שרת Flask עם endpoints לבדיקה ותמצות
├── utils.py               # פונקציות לעיבוד, חילוץ JSON, שמירה ל־LaTeX
├── connect_drive.py       # התחברות ל־Google Drive ושליפת קבצים
├── drive_utils.py         # פונקציות עזר לשימוש ב־Drive
├── client_secrets.json    # קובץ OAuth (לא לשתף ציבורית)
├── graded_table.tex       # טבלת הערות שנוצרת אוטומטית
</pre>

<h2>🔌 API Endpoints</h2>

<ul>
<li><code>POST /grade</code><br>
  קלט: קובץ PDF/LaTeX + קובץ קונטקסט<br>
  פלט: JSON עם הערות וציונים + קובץ LaTeX של טבלה
</li>
<li><code>POST /summary</code><br>
  קלט: JSON עם feedback<br>
  פלט: ציון סופי והערה מסכמת
</li>
</ul>

<h2>🛠️ איך מריצים</h2>

<pre><code>
pip install -r requirements.txt
python app.py
</code></pre>

<h2>🌐 Google Drive Integration</h2>

<ul>
<li>טען את קובץ <code>client_secrets.json</code> מ־Google Cloud Console</li>
<li>התחבר דרך הדפדפן עם PyDrive</li>
<li>שלוף קבצים מתיקיות משותפות והורד אוטומטית PDF</li>
</ul>

<h2>✍️ דוגמת פלט</h2>

<pre><code>[
  {
    "שאלה": "2",
    "סעיף": "ב",
    "ציון": 85,
    "הערה": "ההוכחה תקפה אך חסר נימוק פורמלי במקרה הקצה."
  }
]
</code></pre>

<hr>

<p align="center">
  נבנה באהבה ❤️ כדי לעזור לסטודנטים ולמערכת ההשכלה הגבוהה – גם כשהכיתה מלאה והבודקים חסרים.
</p>

</body>
</html>
