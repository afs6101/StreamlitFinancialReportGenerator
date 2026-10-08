"""
Streamlit Financial Report Generator (FPDF2 Version - Python 3.14 Compatible)
Run with: streamlit run financial_report_streamlit_app.py

Staff uploads CSV/Excel → Gets PDF summary report + CSV downloads
"""

# ===== IMPORT LIBRARIES =====
# pandas = read/organize data from files
# numpy = numeric calculations
# fpdf2 = create PDF documents (ReportLab replacement, works on Python 3.14)
# streamlit = turn Python into interactive web app
# datetime = work with dates/times
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from fpdf import FPDF
import io

# ===== SET UP WEB PAGE =====
# This configures how the page looks in the browser
st.set_page_config(
    page_title="Penn State Financial Reports",  # Shows in browser tab
    page_icon="📊",  # Icon next to title
    layout="wide"  # Make page use full width
)

# ===== MAIN TITLE =====
st.title("📊 Financial Report Generator")
st.markdown("*Upload your SIMBA CSV/Excel file to generate summary and forecast reports*")

# ===== SIDEBAR INFO =====
# Sidebar = gray area on left side of page
# Shows instructions and user info
with st.sidebar:
    st.markdown("### How it works:")
    st.markdown("""
    1. Upload your SIMBA export file
    2. View department summary & spending forecast
    3. Download PDF summary report
    4. Download individual CSV files
    """)
    st.markdown("---")
    st.markdown("**Prepared for:** Penn State AE Department \n\n**Developer:** Amin Sepehri")

# ===== FILE UPLOAD WIDGET =====
# Creates a button where users can select a file from their computer
uploaded_file = st.file_uploader(
    "Upload your SIMBA file (CSV or XLSX)",
    type=["csv", "xlsx"],  # Only accept these file types
    help="This file will not be stored; it's processed in memory only."
)

# ===== ONLY RUN CODE BELOW IF USER UPLOADED A FILE =====
if uploaded_file is not None:
    
    # ===== LOAD DATA =====
    # Read the uploaded file into a Pandas dataframe (think: Excel sheet in Python)
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)  # Read CSV format
        else:
            df = pd.read_excel(uploaded_file)  # Read Excel format
        
        # Show success message to user
        st.success(f"✓ File loaded: {len(df)} rows, {len(df.columns)} columns")
        
    except Exception as e:
        # If file reading fails, show error and stop
        st.error(f"❌ Error reading file: {str(e)}")
        st.stop()
    
    # ===== CREATE TABS =====
    # Create 4 tabs: Summary, Forecast, Department Breakdown, Downloads
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 Summary", "📈 Spending Forecast", "🏢 Department Breakdown", "⬇️ Download Reports"]
    )
    
    # ====================================================================
    # TAB 1: DEPARTMENT SUMMARY
    # ====================================================================
    # Shows total budget, spending, and available balance for each department
    with tab1:
        st.subheader("Department Financial Summary")
        
        # Group data by department and add up all budgets, spending, etc.
        dept_summary = df.groupby('Business Area Name').agg({
            'Budget': 'sum',        # Total budgeted money
            'Actuals': 'sum',       # Total money actually spent
            'Commitments': 'sum',   # Money committed/obligated but not yet spent
            'Available Balances': 'sum'  # Money still available to spend
        }).round(2)
        
        # Calculate what percentage of budget has been spent
        dept_summary['Spending %'] = (
            abs(dept_summary['Actuals']) / abs(dept_summary['Budget']) * 100
        ).round(1)
        
        # Rename column headers to be clearer
        dept_summary = dept_summary.rename(columns={
            'Budget': 'Total Budget',
            'Actuals': 'Total Spent',
            'Commitments': 'Committed',
            'Available Balances': 'Available',
            'Spending %': 'Spending %'
        })
        
        # Format money columns to show as "$1,234.00" instead of raw numbers
        display_summary = dept_summary.copy()
        for col in ['Total Budget', 'Total Spent', 'Committed', 'Available']:
            display_summary[col] = display_summary[col].apply(lambda x: f"${x:,.0f}")
        
        # Display the table on the web page
        st.dataframe(display_summary, use_container_width=True)
        
        # Create a CSV version in memory (not saved to disk yet)
        csv_buffer = io.StringIO()
        dept_summary.to_csv(csv_buffer)
        
        # Show download button for CSV
        st.download_button(
            label="📥 Download Summary as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"Department_Summary_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )
    
    # ====================================================================
    # TAB 2: 12-MONTH SPENDING FORECAST
    # ====================================================================
    # Predicts if departments will overspend by end of fiscal year
    with tab2:
        st.subheader("12-Month Spend Forecast & Risk Analysis")
        
        # Let user input how many months have passed so far
        col1, col2 = st.columns(2)  # Split screen into 2 columns
        with col1:
            months_elapsed = st.slider(
                "Months elapsed in fiscal year:",
                min_value=1,
                max_value=11,
                value=5,
                help="Used to project annual spending"
            )
        
        with col2:
            # Show how many months are left
            st.metric("Months Remaining", 12 - months_elapsed)
        
        # ===== FORECAST CALCULATION =====
        # For each line item, predict if it will exceed budget
        forecast_data = []
        
        for _, row in df.iterrows():
            budget = row['Budget']
            actuals = row['Actuals']
            
            # Calculate average spending per month
            if months_elapsed > 0:
                monthly_avg = abs(actuals) / months_elapsed
            else:
                monthly_avg = 0
            
            # Project what annual spending will be if this rate continues
            projected_annual = monthly_avg * 12
            
            # Calculate how much over budget this will be
            if row['Rev/Exp'] == 'Expense' and budget != 0:
                overage = projected_annual - abs(budget)
            else:
                overage = 0
            
            # Assign status based on overage amount
            if overage > abs(budget) * 0.1:  # If over 10% of budget
                status = "🔴 CRITICAL"
            elif overage > 0:  # If over but less than 10%
                status = "🟡 WARNING"
            else:  # If under budget
                status = "🟢 OK"
            
            # Store all this info for the forecast table
            forecast_data.append({
                'Line Item': row['Commitment Item Name'],
                'Current Spend': actuals,
                'Monthly Avg': round(monthly_avg, 2),
                'Projected Annual': round(projected_annual, 2),
                'Budget': budget,
                'Projected Overage': round(overage, 2),
                'Status': status
            })
        
        # Convert list of forecasts into a dataframe (table)
        forecast_df = pd.DataFrame(forecast_data)
        
        # Separate items into categories based on status
        critical = forecast_df[forecast_df['Status'].str.contains('CRITICAL')]
        warning = forecast_df[forecast_df['Status'].str.contains('WARNING')]
        
        # Show summary counts in metric boxes
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔴 Critical Items", len(critical))
        with col2:
            st.metric("🟡 Warning Items", len(warning))
        with col3:
            st.metric("🟢 OK Items", len(forecast_df) - len(critical) - len(warning))
        
        # Show critical items first (most important)
        if len(critical) > 0:
            st.subheader("🔴 Critical Risk Items")
            st.dataframe(critical, use_container_width=True)
        
        # Show warning items
        if len(warning) > 0:
            st.subheader("🟡 Warning Items")
            st.dataframe(warning, use_container_width=True)
        
        # Download button for full forecast
        forecast_csv = forecast_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Full Forecast as CSV",
            data=forecast_csv,
            file_name=f"Forecast_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )
    
    # ====================================================================
    # TAB 3: DEPARTMENT BREAKDOWN
    # ====================================================================
    # Shows detailed breakdown for each department
    with tab3:
        st.subheader("Department-by-Department Breakdown")
        
        # Let user pick which department to view
        departments = sorted(df['Business Area Name'].unique())
        selected_dept = st.selectbox("Select a department:", departments)
        
        # Filter data for selected department
        dept_data = df[df['Business Area Name'] == selected_dept]
        
        # Calculate summary metrics for this department
        total_budget = dept_data['Budget'].sum()
        total_actuals = dept_data['Actuals'].sum()
        total_committed = dept_data['Commitments'].sum()
        available = dept_data['Available Balances'].sum()
        
        # Show metrics in colored boxes
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Budget", f"${total_budget:,.0f}")
        with col2:
            st.metric("Total Spent", f"${total_actuals:,.0f}")
        with col3:
            st.metric("Committed", f"${total_committed:,.0f}")
        with col4:
            st.metric("Available", f"${available:,.0f}")
        
        # Show detailed table for this department
        st.write("**Detailed line items:**")
        detail_df = dept_data[['Commitment Item', 'Commitment Item Name', 'Budget', 
                               'Commitments', 'Actuals', 'Available Balances', 'Rev/Exp']].copy()
        st.dataframe(detail_df, use_container_width=True)
        
        # Download button for this department's data
        dept_csv = dept_data.to_csv(index=False)
        st.download_button(
            label=f"📥 Download {selected_dept} Data as CSV",
            data=dept_csv,
            file_name=f"{selected_dept.replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )
    
    # ====================================================================
    # TAB 4: PDF REPORT GENERATION
    # ====================================================================
    # Creates a professional PDF summary report
    with tab4:
        st.subheader("Generate PDF Summary Report")
        
        # ===== HELPER FUNCTION: CREATE PDF WITH FPDF2 =====
        # This function builds a PDF document with financial summary
        def generate_pdf_report(df, filename):
            """
            Create a PDF report using FPDF2
            Includes: title, summary table, and forecast table
            """
            
            # Initialize PDF object (letter size, portrait orientation)
            pdf = FPDF()
            pdf.add_page()  # Add first page
            pdf.set_font("Arial", "B", 16)  # Bold, 16pt font for title
            
            # Add title
            pdf.cell(0, 10, "Penn State Faculty Financial Report", ln=True, align="C")
            
            # Add report date
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
            pdf.ln(5)  # Add spacing
            
            # ===== DEPARTMENT SUMMARY TABLE =====
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Department Summary", ln=True)
            pdf.set_font("Arial", "", 9)
            
            # Group by department
            dept_summary = df.groupby('Business Area Name').agg({
                'Budget': 'sum',
                'Actuals': 'sum',
                'Available Balances': 'sum'
            }).round(2)
            
            # Add table header
            pdf.set_fill_color(200, 200, 200)  # Gray background for header
            pdf.cell(50, 8, "Department", border=1, fill=True)
            pdf.cell(40, 8, "Budget", border=1, fill=True)
            pdf.cell(40, 8, "Actuals", border=1, fill=True)
            pdf.cell(40, 8, "Available", border=1, fill=True)
            pdf.ln()
            
            # Add data rows
            for dept, row in dept_summary.iterrows():
                pdf.cell(50, 8, dept[:20], border=1)  # Department name (truncate if long)
                pdf.cell(40, 8, f"${row['Budget']:,.0f}", border=1)
                pdf.cell(40, 8, f"${row['Actuals']:,.0f}", border=1)
                pdf.cell(40, 8, f"${row['Available Balances']:,.0f}", border=1)
                pdf.ln()
            
            pdf.ln(5)  # Add spacing
            
            # ===== HIGH-RISK ITEMS =====
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "High-Risk Spending Items (Forecast)", ln=True)
            pdf.set_font("Arial", "", 9)
            
            # Calculate risk items
            months_elapsed = 5  # Default to 5 months
            risk_items = []
            
            for _, row in df.iterrows():
                if months_elapsed > 0:
                    monthly_avg = abs(row['Actuals']) / months_elapsed
                    projected_annual = monthly_avg * 12
                    budget = row['Budget']
                    
                    if budget != 0:
                        overage = projected_annual - abs(budget)
                        if overage > abs(budget) * 0.05:  # If over 5%
                            risk_items.append((row['Commitment Item Name'], overage))
            
            # Sort by overage amount (highest first)
            risk_items.sort(key=lambda x: x[1], reverse=True)
            
            if risk_items:
                # Show top 10 risk items
                pdf.set_fill_color(255, 200, 200)  # Light red for risky items
                for item_name, overage in risk_items[:10]:
                    pdf.cell(0, 8, f"{item_name[:50]}: ${overage:,.0f} overage", border=1, fill=True, ln=True)
            else:
                pdf.cell(0, 8, "OK: No high-risk items identified", ln=True)
            
            # ===== FOOTER =====
            pdf.ln(10)
            pdf.set_font("Arial", "I", 8)
            pdf.cell(0, 10, "This report is for internal use. Prepared by Penn State Finance Automation.", align="C")
            
            return pdf.output()  # Return PDF as bytes
        
        # ===== CREATE AND DOWNLOAD PDF =====
        # Generate PDF when user clicks button
        if st.button("📄 Generate PDF Report"):
            pdf_bytes = generate_pdf_report(df, "Financial_Report.pdf")
            
            # Show success message
            st.success("✓ PDF generated successfully!")
            
            # Create download button for PDF
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_bytes,
                file_name=f"Financial_Report_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                mime="application/pdf"
            )
        
        # ===== ALSO OFFER COMBINED DOWNLOAD =====
        st.markdown("---")
        st.subheader("Download All Reports at Once")
        
        # Create all CSV files
        csv_files = {}
        
        # 1. Department summary
        dept_summary = df.groupby('Business Area Name').agg({
            'Budget': 'sum',
            'Actuals': 'sum',
            'Commitments': 'sum',
            'Available Balances': 'sum'
        }).round(2)
        csv_files['Department_Summary.csv'] = dept_summary.to_csv()
        
        # 2. Individual department files
        for dept in df['Business Area Name'].unique():
            dept_data = df[df['Business Area Name'] == dept]
            csv_files[f"{dept.replace(' ', '_')}.csv"] = dept_data.to_csv(index=False)
        
        # Show list of files available
        st.write("**Files available for download:**")
        for filename in csv_files.keys():
            st.write(f"  • {filename}")
