# 🚀 FinAI: Intelligent Expense Tracker & Financial Advisor

An advanced, full-stack personal finance application built with Django. FinAI goes beyond traditional expense tracking by integrating **Computer Vision (OCR)** for automated receipt scanning and **Large Language Models (Google Gemini 2.5)** to provide an interactive, RAG-based financial advisor and smart auto-categorization.

## ✨ Key Features

* **🤖 Built-in AI Financial Advisor:** A floating, context-aware chatbot that reads your real-time database to answer questions about your spending habits, provide insights, and alert you to budget anomalies.
* **✨ AI Auto-Categorization:** Type a description (e.g., "Netflix" or "Uber") and the AI will automatically select the correct custom category from your database using fuzzy-matching.
* **📸 OCR Receipt Scanning:** Upload an image of a receipt, and the backend utilizes Tesseract OCR to extract the total amount and automatically fill your expense forms.
* **📊 Dynamic Data Visualization:** Interactive pie charts for category breakdowns and 6-month line graphs for spending trends, powered by Chart.js.
* **🌓 Responsive Light/Dark Mode:** A premium UI that automatically syncs with the user's system preferences, utilizing CSS variables for seamless theme switching.
* **📥 Advanced Exporting:** Download your financial history as formatted CSVs or PDFs for tax purposes and record keeping.
* **🎯 Savings Goals & Budget Alerts:** Set custom monthly limits per category and visual savings goals with dynamic progress bars.

## 🛠️ Tech Stack

* **Backend:** Python, Django, SQLite (Development)
* **Frontend:** HTML5, CSS3, Vanilla JavaScript, Chart.js
* **AI & Machine Learning:** Google GenAI SDK (Gemini 2.5 Flash)
* **Computer Vision:** Tesseract OCR (pytesseract), Pillow (PIL)
* **Document Generation:** xhtml2pdf, Python CSV library

