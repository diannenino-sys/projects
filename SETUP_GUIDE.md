# Settlement Report Automation Setup

This guide walks you through setting up the automation in 5 simple steps.

## Step-by-Step Setup

### ✅ Step 1: Create the Required Folders

1. Open your GitHub repository: https://github.com/diannenino-sys/projects
2. Click the "Add file" button → "Create new file"
3. Type: `settlement_data/.gitkeep` and click "Commit changes"
4. Repeat and create: `settlement_results/.gitkeep`

**Result:** You now have two folders:
- `settlement_data/` - where you upload CSV files
- `settlement_results/` - where results appear

### ✅ Step 2: Upload Your First Settlement Report

1. Go to the `settlement_data/` folder
2. Click "Add file" → "Upload files"
3. Select your settlement CSV file (e.g., `settlement_2026-06-01.csv`)
4. Click "Commit changes"

### ✅ Step 3: Watch the Automation Run

1. Click the "Actions" tab in your repository
2. You should see "Process Settlement Reports" workflow running
3. Wait for it to complete (usually takes 1-3 minutes)
4. You'll see a ✅ green checkmark when done

### ✅ Step 4: View Your Results

1. Go to the `settlement_results/` folder
2. You'll see two new files:
   - **CONSOLIDATED_SUMMARY.html** - Click to open in browser
   - **CONSOLIDATED_SUMMARY.csv** - Download to open in Excel

### ✅ Step 5: Automate Daily

Every day, just:
1. Upload your new settlement CSV to `settlement_data/` folder
2. The automation runs automatically
3. Results update in `settlement_results/` folder

---

## 🎯 Key Features

✅ **Automatic Processing** - Just drop CSV files, automation handles the rest
✅ **Multi-file Support** - Process multiple files, get consolidated summary
✅ **Beautiful Dashboard** - HTML report with charts and clean layout
✅ **Excel Export** - CSV file for detailed analysis
✅ **Tax Calculations** - Automatic VAT and withholding tax breakdown
✅ **Large File Support** - Handles 100MB+ files with 400k+ rows
✅ **Date-based Summaries** - Organized by daily, weekly, monthly periods

---

## 📞 Need Help?

1. Check the Actions tab for error messages
2. Make sure CSV files are in the `settlement_data/` folder
3. Ensure CSV has required columns: settlement_txn_id, transaction_type, transaction_amount, net_mdr, settle_amount

---

**You're all set! 🚀 Start uploading settlement files and watch the magic happen.**
