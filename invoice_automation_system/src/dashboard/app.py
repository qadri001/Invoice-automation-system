"""Streamlit dashboard for invoice automation system."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from storage.database import InvoiceDatabase
from alerts.alert_manager import AlertManager

# Page configuration
st.set_page_config(
    page_title="Invoice Automation Dashboard",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .status-validated {
        color: #28a745;
        font-weight: bold;
    }
    .status-pending {
        color: #ffc107;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    .alert-critical {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 10px;
        margin: 5px 0;
    }
    .alert-warning {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 10px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_database():
    """Get database instance."""
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'database', 'invoices.db')
    return InvoiceDatabase(db_path)

def render_header():
    """Render dashboard header."""
    st.markdown('<div class="main-header">📄 Smart Invoice Automation System</div>', 
                unsafe_allow_html=True)
    st.markdown("AI-powered invoice processing, validation, and analytics")

def render_metrics(db: InvoiceDatabase):
    """Render key metrics."""
    stats = db.get_statistics()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Invoices",
            value=stats.get('total_invoices', 0),
            delta=f"+{stats.get('recent_count', 0)} this week"
        )

    with col2:
        total_amount = stats.get('total_amount', 0)
        st.metric(
            label="Total Processed",
            value=f"${total_amount:,.2f}"
        )

    with col3:
        avg_conf = stats.get('avg_confidence', 0)
        st.metric(
            label="Avg Confidence",
            value=f"{avg_conf:.1%}"
        )

    with col4:
        status_breakdown = stats.get('status_breakdown', {})
        pending = status_breakdown.get('pending', 0)
        st.metric(
            label="Pending Review",
            value=pending,
            delta_color="inverse"
        )

def render_status_chart(db: InvoiceDatabase):
    """Render status breakdown chart."""
    stats = db.get_statistics()
    status_data = stats.get('status_breakdown', {})

    if status_data:
        fig = px.pie(
            values=list(status_data.values()),
            names=list(status_data.keys()),
            title="Invoice Status Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig, use_container_width=True)

def render_recent_invoices(db: InvoiceDatabase):
    """Render recent invoices table."""
    st.subheader("Recent Invoices")

    invoices = db.get_all_invoices(limit=20)

    if invoices:
        # Prepare data for display
        display_data = []
        for inv in invoices:
            display_data.append({
                'ID': inv['id'],
                'Vendor': inv['vendor_name'] or 'Unknown',
                'Invoice #': inv['invoice_number'] or 'N/A',
                'Date': inv['invoice_date'] or 'N/A',
                'Amount': f"${inv['total_amount']:,.2f}" if inv['total_amount'] else 'N/A',
                'Status': inv['status'],
                'Processed': inv['processed_at']
            })

        df = pd.DataFrame(display_data)

        # Color code status
        def color_status(val):
            if val == 'approved':
                return 'background-color: #d4edda'
            elif val == 'pending':
                return 'background-color: #fff3cd'
            elif val == 'rejected':
                return 'background-color: #f8d7da'
            return ''

        st.dataframe(
            df.style.applymap(color_status, subset=['Status']),
            use_container_width=True
        )
    else:
        st.info("No invoices processed yet")

def render_alerts():
    """Render alerts section."""
    st.subheader("🚨 Recent Alerts")

    # This would be populated from alert manager in production
    # For now, show placeholder
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="alert-critical">
            <strong>Duplicate Detected</strong><br>
            Invoice INV-2024-001 from Acme Corp appears to be a duplicate
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="alert-warning">
            <strong>High Amount Alert</strong><br>
            Invoice amount $15,000 exceeds threshold
        </div>
        """, unsafe_allow_html=True)

def render_upload_section():
    """Render file upload section."""
    st.subheader("📤 Upload New Invoice")

    uploaded_file = st.file_uploader(
        "Choose a PDF or image file",
        type=['pdf', 'png', 'jpg', 'jpeg', 'tiff'],
        help="Upload invoice for immediate processing"
    )

    if uploaded_file is not None:
        # Save uploaded file
        input_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'invoices')
        os.makedirs(input_dir, exist_ok=True)

        file_path = os.path.join(input_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"File uploaded: {uploaded_file.name}")
        st.info("File will be processed automatically by the watcher service")

def render_analytics(db: InvoiceDatabase):
    """Render analytics charts."""
    st.subheader("📊 Processing Analytics")

    invoices = db.get_all_invoices(limit=100)

    if invoices:
        df = pd.DataFrame(invoices)

        # Amount over time
        if 'invoice_date' in df.columns and 'total_amount' in df.columns:
            df['invoice_date'] = pd.to_datetime(df['invoice_date'], errors='coerce')
            df = df.dropna(subset=['invoice_date'])

            if not df.empty:
                fig = px.line(
                    df.sort_values('invoice_date'),
                    x='invoice_date',
                    y='total_amount',
                    title='Invoice Amounts Over Time',
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)

        # Vendor distribution
        if 'vendor_name' in df.columns:
            vendor_counts = df['vendor_name'].value_counts().head(10)
            fig = px.bar(
                x=vendor_counts.index,
                y=vendor_counts.values,
                title='Top 10 Vendors by Invoice Count',
                labels={'x': 'Vendor', 'y': 'Count'}
            )
            st.plotly_chart(fig, use_container_width=True)

def render_settings():
    """Render settings section."""
    st.subheader("⚙️ System Settings")

    with st.expander("OCR Engine Settings"):
        ocr_engine = st.selectbox(
            "OCR Engine",
            ['paddleocr', 'tesseract', 'hybrid'],
            index=0
        )
        confidence_threshold = st.slider(
            "Confidence Threshold",
            0.0, 1.0, 0.6
        )

    with st.expander("Validation Rules"):
        max_amount = st.number_input(
            "Maximum Amount Alert Threshold",
            value=10000.0,
            step=1000.0
        )
        duplicate_days = st.number_input(
            "Duplicate Check Period (days)",
            value=365,
            step=30
        )

    with st.expander("Alert Configuration"):
        st.checkbox("Enable Email Alerts")
        st.checkbox("Enable Slack Alerts")
        st.checkbox("Enable Console Alerts", value=True)

def main():
    """Main dashboard application."""
    render_header()

    # Initialize database
    db = get_database()

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Dashboard", "Invoices", "Upload", "Analytics", "Settings"]
    )

    if page == "Dashboard":
        render_metrics(db)

        col1, col2 = st.columns([2, 1])
        with col1:
            render_recent_invoices(db)
        with col2:
            render_status_chart(db)

        render_alerts()

    elif page == "Invoices":
        render_recent_invoices(db)

        # Invoice detail view
        st.subheader("Invoice Details")
        invoice_id = st.number_input("Enter Invoice ID", min_value=1, value=1)

        if st.button("View Details"):
            invoice = db.get_invoice(invoice_id)
            if invoice:
                st.json(invoice)
            else:
                st.error("Invoice not found")

    elif page == "Upload":
        render_upload_section()

    elif page == "Analytics":
        render_analytics(db)

    elif page == "Settings":
        render_settings()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("Invoice Automation System v1.0")

if __name__ == "__main__":
    main()
