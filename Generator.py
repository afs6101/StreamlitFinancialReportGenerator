"""
Streamlit Financial Report Generator
Run with: streamlit run financial_report_streamlit_app.py

Staff uploads CSV/Excel → Gets PDF summary report + CSV downloads
"""

# ===== IMPORT LIBRARIES =====
# These are tools Python needs to do specific jobs:
# pandas = read/organize data from files
# reportlab = create PDF documents
# streamlit = turn Python into interactive web app
# datetime = work with dates/times
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
import io

# ===== SET UP WEB PAGE =====
# This configures how the page looks in the browser
st.set_page_config(
    page_title="Penn State Financial Reports",  # Shows in browser tab
    page_icon="📊",  # Icon next to title
    layout="wide"  # Make page use full width
)

# ===== MAIN TITLE =====
st.title("📊 Faculty Financial Report Generator")
st.markdown("*Upload your SIMBA CSV/Excel file to generate summary and forecast reports*")

# ===== SIDEBAR INFO =====
# Sidebar = gray area on left side of page
# Shows instructions and user info
with st.sidebar:
    st.markdown("### How it works:")
    st.markdown("""
    1. Upload your SIMBA export file (CSV or Excel)
    2. View department summary & spending forecast
    3. Download PDF summary report
    4. Download individual CSV files
    """)
    st.markdown("---")
    st.markdown("**Prepared for:** Penn State Finance\n\n**User:** afs6101@psu.edu")

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
        
        # Show summary counts in 3 boxes
        col1, col2, col3 = st.columns(3)
        col1.metric("Critical Items", len(critical))
        col2.metric("Warning Items", len(warning))
        col3.metric("On-Track Items", len(forecast_df) - len(critical) - len(warning))
        
        # Display critical items (big red section)
        if len(critical) > 0:
            st.error(f"**🔴 Critical Items ({len(critical)})**")
            for _, item in critical.iterrows():
                st.write(f"- **{item['Line Item']}**  \nProjected: ${item['Projected Annual']:,.0f} vs Budget: ${item['Budget']:,.0f} → Overage: ${item['Projected Overage']:,.0f}")
        
        # Display warning items (yellow section)
        if len(warning) > 0:
            st.warning(f"**🟡 Warning Items ({len(warning)})**")
            for _, item in warning.head(5).iterrows():
                st.write(f"- **{item['Line Item']}**  \nProjected: ${item['Projected Annual']:,.0f} vs Budget: ${item['Budget']:,.0f} → Overage: ${item['Projected Overage']:,.0f}")
        
        # Create CSV version in memory
        csv_buffer = io.StringIO()
        forecast_df.to_csv(csv_buffer, index=False)
        
        # Show download button
        st.download_button(
            label="📥 Download Forecast as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"Spend_Forecast_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )
    
    # ====================================================================
    # TAB 3: INDIVIDUAL DEPARTMENT BREAKDOWN
    # ====================================================================
    # Let user pick one department and see all its line items in detail
    with tab3:
        st.subheader("Select a Department for Detailed Breakdown")
        
        # Create dropdown menu with all departments
        departments = sorted(df['Business Area Name'].unique())
        selected_dept = st.selectbox("Choose department:", departments)
        
        # Filter data to only show selected department
        dept_data = df[df['Business Area Name'] == selected_dept]
        
        # Show key metrics in 4 boxes
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Budget", f"${dept_data['Budget'].sum():,.0f}")
        col2.metric("Total Spent", f"${dept_data['Actuals'].sum():,.0f}")
        col3.metric("Committed", f"${dept_data['Commitments'].sum():,.0f}")
        col4.metric("Available", f"${dept_data['Available Balances'].sum():,.0f}")
        
        # Show detailed table of all line items in this department
        st.markdown(f"**Line Items for {selected_dept}**")
        detail_table = dept_data[['Commitment Item', 'Commitment Item Name', 'Budget', 
                                   'Actuals', 'Available Balances', 'Rev/Exp']].copy()
        
        # Format money columns
        for col in ['Budget', 'Actuals', 'Available Balances']:
            detail_table[col] = detail_table[col].apply(lambda x: f"${x:,.0f}")
        
        # Display table
        st.dataframe(detail_table, use_container_width=True)
        
        # Create CSV version
        csv_buffer = io.StringIO()
        dept_data.to_csv(csv_buffer, index=False)
        
        # Download button
        st.download_button(
            label=f"📥 Download {selected_dept} Report as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"{selected_dept}_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )
    
    # ====================================================================
    # TAB 4: PDF DOWNLOAD
    # ====================================================================
    # Generate a professional PDF report with all summary information
    with tab4:
        st.subheader("Download PDF Summary Report")
        
        # Create PDF in memory (not saved to disk)
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        
        # Container for all content that will go in the PDF
        story = []
        
        # Define text styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#003366'),
            spaceAfter=12
        )
        
        # Add title
        story.append(Paragraph("Penn State Faculty Financial Report", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Add metadata
        story.append(Paragraph(f"<b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Paragraph(f"<b>Total Records:</b> {len(df)}", styles['Normal']))
        story.append(Paragraph(f"<b>Departments:</b> {len(df['Business Area Name'].unique())}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Add department summary table
        story.append(Paragraph("Department Summary", styles['Heading2']))
        
        # Convert summary dataframe to table format for PDF
        summary_data = [['Department', 'Total Budget', 'Total Spent', 'Available', 'Spending %']]
        for idx, row in dept_summary.iterrows():
            summary_data.append([
                str(idx),
                f"${row['Total Budget']:,.0f}",
                f"${row['Total Spent']:,.0f}",
                f"${row['Available']:,.0f}",
                f"{row['Spending %']:.1f}%"
            ])
        
        # Create table object with formatting
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Add forecast summary
        story.append(Paragraph("12-Month Spending Forecast", styles['Heading2']))
        critical_count = len(forecast_df[forecast_df['Status'] == '🔴 CRITICAL'])
        warning_count = len(forecast_df[forecast_df['Status'] == '🟡 WARNING'])
        story.append(Paragraph(f"Critical Items: {critical_count} | Warning Items: {warning_count}", styles['Normal']))
        
        # Build the PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_data = pdf_buffer.getvalue()
        
        # Show download button for PDF
        st.download_button(
            label="📥 Download as PDF",
            data=pdf_data,
            file_name=f"Financial_Report_{datetime.now().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf"
        )
        
        st.success("✓ PDF ready to download!")
