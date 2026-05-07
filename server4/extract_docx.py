import sys
import subprocess

try:
    import docx
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
    import docx

def main():
    file_path = "D:/Desktop/New_Flask/FLASK/server4/AI Presentation Tool Technical Research.docx"
    try:
        doc = docx.Document(file_path)
        text = []
        for p in doc.paragraphs:
            text.append(p.text)
        with open("parsed_research.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(text))
        print("Successfully parsed DOCX to parsed_research.txt")
    except Exception as e:
        print(f"Error parsing document: {e}")
    except Exception as e:
        print(f"Error parsing document: {e}")

if __name__ == "__main__":
    main()