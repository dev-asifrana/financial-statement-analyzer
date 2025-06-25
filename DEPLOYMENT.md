# 🚀 Deployment Guide - GitHub + Streamlit Cloud

Follow these simple steps to deploy your Financial Statement Analyzer to the web for free!

## Step 1: Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the **"New"** button (green button) to create a new repository
3. Repository settings:
   - **Repository name**: `financial-statement-analyzer` (or any name you prefer)
   - **Description**: `AI-powered Canadian bank statement analyzer`
   - **Visibility**: Public ✅
   - **Initialize with README**: ❌ (we already have one)
4. Click **"Create repository"**

## Step 2: Upload Your Files

### Option A: Web Interface (Easiest)
1. In your new GitHub repository, click **"uploading an existing file"**
2. Drag and drop these files from your project:
   ```
   📁 Your files to upload:
   ├── app_clean.py
   ├── smart_document_processor_v2.py  
   ├── ai_categorizer.py
   ├── category_manager.py (if you have it)
   ├── requirements.txt
   ├── README.md
   ├── LICENSE
   ├── .gitignore
   ├── DEPLOYMENT.md
   └── assets/logo.png (if you have it)
   ```
3. Add commit message: `Initial commit - Financial Statement Analyzer`
4. Click **"Commit changes"**

### Option B: Git Command Line
```bash
git init
git add .
git commit -m "Initial commit - Financial Statement Analyzer"
git branch -M main
git remote add origin https://github.com/yourusername/financial-statement-analyzer.git
git push -u origin main
```

## Step 3: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"Sign in with GitHub"**
3. Click **"New app"**
4. Fill in the deployment form:
   - **Repository**: Select your `financial-statement-analyzer` repo
   - **Branch**: `main`
   - **Main file path**: `app_clean.py`
   - **App URL**: Choose a custom name (optional)
5. Click **"Deploy!"**

## Step 4: Wait for Deployment

- ⏱️ **Initial deployment**: 2-5 minutes
- 🔄 **Status**: Watch the logs in real-time
- ✅ **Complete**: You'll get a public URL like `https://your-app-name.streamlit.app`

## Step 5: Share Your App

Once deployed, you get:
- 🌐 **Public URL** - Share with anyone
- 🔄 **Auto-updates** - Pushes to GitHub automatically redeploy
- 📊 **Usage analytics** - See how many people use your app
- 🆓 **Free hosting** - No costs, no credit card required

## 🛠️ Troubleshooting

### Common Issues:

**1. Module not found errors**
- Check that all imports in your code match your file names
- Ensure `requirements.txt` includes all dependencies

**2. App won't start**
- Check the Streamlit Cloud logs for specific error messages
- Verify your `app_clean.py` file is in the root directory

**3. Missing logo**
- Create an `assets` folder in your repo
- Upload your logo as `assets/logo.png`

### 🆘 Need Help?
- Check Streamlit Cloud logs for error details
- Visit [Streamlit Community Forum](https://discuss.streamlit.io/)
- Create an issue in this GitHub repository

## 🎉 Success!

Your Financial Statement Analyzer is now live and accessible to anyone with the URL!

**Next Steps:**
- Share the URL with friends and colleagues
- Add screenshots to your README
- Consider adding more features
- Collect user feedback

---

*Happy deploying! 🚀* 