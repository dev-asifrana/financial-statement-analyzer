# Financial Statement Analyzer 📊

A sophisticated Canadian bank statement processing and analysis tool with AI-powered transaction categorization and professional insights.

## 🌟 Overview

Financial Statement Analyzer is a comprehensive solution for processing PDF bank statements from major Canadian financial institutions. Using advanced AI categorization and intelligent document processing, it transforms raw bank statements into actionable financial insights.

## 🏦 Supported Banks

### Major Canadian Banks (Currently Supported)
- **Royal Bank of Canada (RBC)** - Bank statements and credit cards
- **TD Bank** - Bank statements and credit cards  
- **Bank of Montreal (BMO)** - Bank statements and credit cards
- **Scotiabank** - Bank statements and credit cards
- **CIBC** - Bank statements and credit cards
- **Tangerine** - Bank statements and credit cards
- **Simplii Financial** - Bank statements and credit cards
- **EQ Bank** - Bank statements
- **American Express Canada** - Credit card statements
- **Wise** - Multi-currency statements

### Coming Soon 🚀
- Credit unions across Canada
- Additional regional banks
- US bank statement support
- International bank formats

## ✨ Key Features

### 🤖 Intelligent Processing
- **Auto-Detection** - Automatically identifies bank formats
- **16 Specialized Processors** - Dedicated logic for each bank
- **AI-Powered Categorization** - Smart transaction classification
- **Multi-Format Support** - Handles various PDF layouts

### 📈 Professional Analytics
- **Spending Overview** - Comprehensive financial dashboard
- **Category Breakdown** - Detailed spending analysis
- **Monthly Trends** - Track spending patterns over time
- **Interactive Charts** - Modern visualizations with Plotly
- **Budget Tracking** - Compare actual vs planned spending

### 🎨 Modern Interface
- **Clean Design** - Professional, business-ready interface
- **Dark Sidebar** - Elegant navigation with logo support
- **Responsive Layout** - Works on desktop and mobile
- **Interactive Cards** - Click-to-navigate dashboard cards

### 🔐 Privacy First
- **100% Local Processing** - Your data never leaves your device
- **No Cloud Storage** - All analysis happens locally
- **Secure** - No data transmission to external servers
- **GDPR Compliant** - Complete data privacy

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Required dependencies (see requirements.txt)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/financial-statement-analyzer.git
   cd financial-statement-analyzer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app_clean.py
   ```

4. **Open your browser**
   - Navigate to `http://localhost:8501`
   - Upload your PDF bank statements
   - Start analyzing!

## 📱 Usage

### 1. Upload Documents
- Drag and drop PDF bank statements
- Supports multiple files simultaneously
- Automatic bank format detection

### 2. AI Processing
- Intelligent document parsing
- Transaction extraction and validation
- Smart categorization with confidence scores

### 3. Analyze Results
- **Overview Tab** - Key metrics and spending summary
- **Charts Tab** - Visual spending analysis and trends
- **Transactions Tab** - Detailed transaction breakdown
- **Reports Tab** - Exportable insights and summaries

### 4. Category Management
- View and edit transaction categories
- Add custom categories with keywords
- Manage spending budgets and goals

## 🛠️ Technology Stack

### Backend
- **Python 3.8+** - Core application language
- **Streamlit** - Web application framework
- **Pandas** - Data manipulation and analysis
- **PyPDF2 & PDFPlumber** - PDF processing
- **Sentence Transformers** - AI-powered categorization

### Frontend
- **Streamlit** - Interactive web interface
- **Plotly** - Modern, interactive charts
- **Custom CSS** - Professional styling
- **Responsive Design** - Mobile-friendly layout

### AI & Machine Learning
- **Hugging Face Transformers** - Natural language processing
- **Keyword Matching** - Rule-based categorization
- **Confidence Scoring** - Transaction classification accuracy

## 📊 Screenshots

*Screenshots will be added soon showcasing the dashboard, analytics, and category management features.*

## 🗺️ Roadmap

### Version 2.0 (Coming Soon)
- [ ] Additional Canadian banks and credit unions
- [ ] Enhanced AI categorization with custom models
- [ ] Export to Excel and CSV formats
- [ ] Multi-currency support improvements
- [ ] Batch processing for large statement volumes

### Version 3.0 (Future)
- [ ] US bank statement support
- [ ] Investment account analysis
- [ ] Advanced financial forecasting
- [ ] Mobile app companion
- [ ] API access for developers

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### Adding New Bank Support
1. Fork the repository
2. Add processor logic in `smart_document_processor_v2.py`
3. Test with sample statements
4. Submit a pull request

### Improving Categorization
1. Enhance keyword lists in category management
2. Improve AI model accuracy
3. Add new spending categories

### Bug Reports & Feature Requests
- Use GitHub Issues to report bugs
- Suggest new features and improvements
- Help with testing and validation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to the open-source community for excellent libraries
- Hugging Face for transformer models
- Streamlit team for the amazing framework
- Contributors and testers for their valuable feedback

## 📞 Support

For support, feature requests, or questions:
- 📧 Create an issue on GitHub
- 💬 Join our discussions
- 📝 Check the documentation

---

**⭐ Star this repository if you find it useful!**

*Built with ❤️ for the Canadian financial community* 