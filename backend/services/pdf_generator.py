import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from services.market_data import fetch_quote
import models

def generate_pdf_report(portfolio: models.Portfolio) -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "reports")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    safe_name = portfolio.name.replace(" ", "_")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_name}_Report_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    title_style = styles['Title']
    normal_style = styles['Normal']
    heading_style = styles['Heading2']
    
    elements.append(Paragraph(f"Portfolio Performance Report: {portfolio.name}", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}", normal_style))
    elements.append(Spacer(1, 20))
    
    table_data = [["Symbol", "Shares", "Avg Cost", "Current Price", "Total Value", "Unrealized P/L"]]
    total_portfolio_value = 0.0
    total_cost_basis = 0.0
    
    for asset in portfolio.assets:
        if asset.quantity <= 0:
            continue
            
        try:
            quote = fetch_quote(asset.symbol)
            current_price = quote.price
        except:
            current_price = asset.average_price
            
        current_value = asset.quantity * current_price
        cost_basis = asset.quantity * asset.average_price
        
        total_portfolio_value += current_value
        total_cost_basis += cost_basis
        
        pl_dollars = current_value - cost_basis
        pl_pct = (pl_dollars / cost_basis * 100) if cost_basis > 0 else 0.0
        
        table_data.append([
            asset.symbol,
            f"{asset.quantity:.4f}",
            f"${asset.average_price:.2f}",
            f"${current_price:.2f}",
            f"${current_value:.2f}",
            f"${pl_dollars:.2f} ({pl_pct:.2f}%)"
        ])
        
    total_pl = total_portfolio_value - total_cost_basis
    total_pl_pct = (total_pl / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
    
    t = Table(table_data, colWidths=[60, 60, 80, 80, 100, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 30))
    
    elements.append(Paragraph(f"Total Cost Basis: ${total_cost_basis:.2f}", normal_style))
    elements.append(Paragraph(f"Current Portfolio Value: ${total_portfolio_value:.2f}", heading_style))
    elements.append(Paragraph(f"Total Unrealized P/L: ${total_pl:.2f} ({total_pl_pct:.2f}%)", normal_style))
    
    doc.build(elements)
    return filepath