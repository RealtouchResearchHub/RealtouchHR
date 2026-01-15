"""
RealtouchHR - PDF Service
Generate PDF payslips and reports
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def generate_payslip_pdf(payslip: dict, company: dict, payrun: dict, employee: dict = None) -> bytes:
    """Generate a PDF payslip"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=20*mm, 
        leftMargin=20*mm, 
        topMargin=20*mm, 
        bottomMargin=20*mm
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', 
        parent=styles['Heading1'], 
        fontSize=18, 
        alignment=TA_CENTER, 
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', 
        parent=styles['Normal'], 
        fontSize=10, 
        alignment=TA_CENTER, 
        textColor=colors.grey
    )
    header_style = ParagraphStyle(
        'Header', 
        parent=styles['Heading2'], 
        fontSize=12, 
        spaceAfter=5
    )
    
    elements = []
    
    # Company header
    company_name = company.get("name", "Company") if company else "Company"
    elements.append(Paragraph(company_name, title_style))
    elements.append(Paragraph("PAYSLIP", subtitle_style))
    elements.append(Spacer(1, 10*mm))
    
    # Pay period info
    period_data = [
        ["Pay Period:", f"{payrun.get('period_start', '')} to {payrun.get('period_end', '')}"],
        ["Payment Date:", payrun.get('pay_date', '')],
    ]
    period_table = Table(period_data, colWidths=[60*mm, 100*mm])
    period_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(period_table)
    elements.append(Spacer(1, 5*mm))
    
    # Employee details
    emp_name = payslip.get("employee_name", "")
    if employee:
        emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}"
    
    elements.append(Paragraph("Employee Details", header_style))
    emp_data = [
        ["Name:", emp_name],
        ["Employee ID:", payslip.get('employee_id', '')],
    ]
    if employee:
        if employee.get('ni_number'):
            emp_data.append(["NI Number:", employee.get('ni_number', '')])
        if employee.get('tax_code'):
            emp_data.append(["Tax Code:", employee.get('tax_code', '')])
    
    emp_table = Table(emp_data, colWidths=[60*mm, 100*mm])
    emp_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 8*mm))
    
    # Earnings and Deductions
    elements.append(Paragraph("Earnings & Deductions", header_style))
    
    gross_pay = payslip.get('gross_pay', 0)
    tax = payslip.get('tax_deduction', 0)
    ni = payslip.get('ni_deduction', 0)
    pension = payslip.get('pension_deduction', 0)
    other = payslip.get('other_deductions', 0)
    net_pay = payslip.get('net_pay', 0)
    
    pay_data = [
        ["Description", "Amount (£)"],
        ["Gross Pay", f"{gross_pay:,.2f}"],
        ["", ""],
        ["Deductions:", ""],
        ["Income Tax (PAYE)", f"-{tax:,.2f}"],
        ["National Insurance", f"-{ni:,.2f}"],
        ["Pension Contribution", f"-{pension:,.2f}"],
    ]
    
    if other > 0:
        pay_data.append(["Other Deductions", f"-{other:,.2f}"])
    
    pay_data.extend([
        ["", ""],
        ["Net Pay", f"{net_pay:,.2f}"],
    ])
    
    pay_table = Table(pay_data, colWidths=[100*mm, 60*mm])
    pay_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e7ff')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    elements.append(pay_table)
    elements.append(Spacer(1, 10*mm))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer', 
        parent=styles['Normal'], 
        fontSize=8, 
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(
        f"Generated by RealtouchHR on {datetime.now().strftime('%d %B %Y at %H:%M')}",
        footer_style
    ))
    elements.append(Paragraph(
        "This is a computer-generated document. Please retain for your records.",
        footer_style
    ))
    
    doc.build(elements)
    return buffer.getvalue()


def generate_pay_run_summary_pdf(payrun: dict, payslips: list, company: dict) -> bytes:
    """Generate a PDF summary of an entire pay run"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=15*mm, 
        leftMargin=15*mm, 
        topMargin=15*mm, 
        bottomMargin=15*mm
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', 
        parent=styles['Heading1'], 
        fontSize=16, 
        alignment=TA_CENTER
    )
    
    elements = []
    
    # Header
    company_name = company.get("name", "Company") if company else "Company"
    elements.append(Paragraph(f"{company_name} - Pay Run Summary", title_style))
    elements.append(Spacer(1, 5*mm))
    
    # Pay run info
    info_data = [
        ["Period:", f"{payrun.get('period_start', '')} to {payrun.get('period_end', '')}"],
        ["Pay Date:", payrun.get('pay_date', '')],
        ["Employees:", str(payrun.get('employee_count', len(payslips)))],
        ["Status:", payrun.get('status', '').title()],
    ]
    info_table = Table(info_data, colWidths=[50*mm, 120*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8*mm))
    
    # Employee summary table
    headers = ["Employee", "Gross Pay", "Tax", "NI", "Pension", "Net Pay"]
    table_data = [headers]
    
    for ps in payslips:
        table_data.append([
            ps.get('employee_name', ''),
            f"£{ps.get('gross_pay', 0):,.2f}",
            f"£{ps.get('tax_deduction', 0):,.2f}",
            f"£{ps.get('ni_deduction', 0):,.2f}",
            f"£{ps.get('pension_deduction', 0):,.2f}",
            f"£{ps.get('net_pay', 0):,.2f}",
        ])
    
    # Totals row
    total_gross = sum(ps.get('gross_pay', 0) for ps in payslips)
    total_tax = sum(ps.get('tax_deduction', 0) for ps in payslips)
    total_ni = sum(ps.get('ni_deduction', 0) for ps in payslips)
    total_pension = sum(ps.get('pension_deduction', 0) for ps in payslips)
    total_net = sum(ps.get('net_pay', 0) for ps in payslips)
    
    table_data.append([
        "TOTALS",
        f"£{total_gross:,.2f}",
        f"£{total_tax:,.2f}",
        f"£{total_ni:,.2f}",
        f"£{total_pension:,.2f}",
        f"£{total_net:,.2f}",
    ])
    
    summary_table = Table(table_data, colWidths=[50*mm, 28*mm, 28*mm, 28*mm, 28*mm, 28*mm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e7ff')),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(summary_table)
    
    doc.build(elements)
    return buffer.getvalue()
