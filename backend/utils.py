import json
import re
import os

TABLE_OUTPUT_PATH = "graded_table.tex"

def escape_latex(text: str):
    return (text.replace('\\', r'\\')
                .replace('_', r'\_')
                .replace('%', r'\%')
                .replace('$', r'\$')
                .replace('&', r'\&')
                .replace('#', r'\#')
                .replace('{', r'\{')
                .replace('}', r'\}')
                .replace('^', r'\^{}')
                .replace('~', r'\~{}'))

def extract_valid_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[\s*{.*?}\s*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
        return None

def save_table_to_latex(structured_data, output_path=TABLE_OUTPUT_PATH):
    lines = [
        r"\documentclass{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{bidi}",
        r"\usepackage{geometry}",
        r"\geometry{margin=2.5cm}",
        r"\begin{document}",
        r"\section*{טבלת ציונים}",
        r"\begin{RTL}",
        r"\begin{tabular}{|c|c|c|p{10cm}|}",
        r"\hline",
        r"שאלה & סעיף & ציון & הערה \\",
        r"\hline"
    ]

    for item in structured_data:
        q = item.get("שאלה", "")
        s = item.get("סעיף", "")
        g = item.get("ציון", "")
        c = escape_latex(item.get("הערה", ""))
        lines.append(f"{q} & {s} & {g} & {c} \\\\ \\hline")

    lines += [r"\end{tabular}", r"\end{RTL}", r"\end{document}"]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def summarize_feedback(feedback: list) -> dict:
    '''
    Given a list of feedback items (each with ציון and הערה),
    returns a summary containing average grade and a master comment.
    '''
    scores = [item.get("ציון", 0) for item in feedback if isinstance(item, dict)]
    average = sum(scores) / len(scores) if scores else 0

    if average == 100:
        comment = "הפתרון מושלם – כל הסעיפים נבדקו בהצלחה מלאה."
    elif average >= 85:
        comment = "הפתרון טוב מאוד עם כמה נקודות לשיפור."
    elif average >= 70:
        comment = "יש צורך בחיזוק בחלק מהסעיפים, אך יש הבנה כללית."
    else:
        comment = "נדרש שיפור משמעותי במענה על השאלות."

    return {
        "final_grade": round(average, 2),
        "master_comment": comment
    }
