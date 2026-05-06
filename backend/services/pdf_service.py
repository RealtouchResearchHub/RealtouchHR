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


# ==================== HMRC TAX DOCUMENTS ====================

def _base_doc(title: str):
    """Create a base SimpleDocTemplate with common styles"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title=title
    )
    styles = getSampleStyleSheet()
    return buffer, doc, styles


def generate_p45_pdf(employee: dict, company: dict, p45_data: dict) -> bytes:
    """
    Generate HMRC P45 - Details of employee leaving work.
    
    p45_data expected keys:
      leaving_date, tax_code, week1_month1_basis (bool),
      total_pay_to_date, total_tax_to_date,
      student_loan_deductions, pay_this_employment, tax_this_employment,
      pay_previous_employment, tax_previous_employment
    """
    buffer, doc, styles = _base_doc("P45")
    title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER)
    sub_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, spaceAfter=4)
    elements = []

    company_name = (company or {}).get("name", "Employer")
    elements.append(Paragraph("P45 - Details of employee leaving work", title_style))
    elements.append(Paragraph("Part 1A - For the employee to keep", sub_style))
    elements.append(Spacer(1, 6*mm))

    # Section 1: Employer details
    paye_ref = (company or {}).get("paye_reference", "")
    elements.append(Paragraph("1. Employer details", h2))
    emp_tbl = Table([
        ["Employer PAYE reference", paye_ref],
        ["Employer name", company_name],
        ["Address", (company or {}).get("address", "")],
    ], colWidths=[65*mm, 105*mm])
    emp_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ]))
    elements.append(emp_tbl)
    elements.append(Spacer(1, 4*mm))

    # Section 2: Employee details
    emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}"
    elements.append(Paragraph("2. Employee details", h2))
    emp2 = Table([
        ["NI number", employee.get("ni_number", "")],
        ["Title / Full name", emp_name],
        ["Leaving date", p45_data.get("leaving_date", "")],
        ["Tax code at leaving", p45_data.get("tax_code", "")],
        ["Week 1/Month 1 basis", "Yes" if p45_data.get("week1_month1_basis") else "No"],
    ], colWidths=[65*mm, 105*mm])
    emp2.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ]))
    elements.append(emp2)
    elements.append(Spacer(1, 4*mm))

    # Section 3: Pay and tax figures
    elements.append(Paragraph("3. Total pay and tax", h2))
    pay_tbl = Table([
        ["", "This employment (£)", "Previous employment (£)", "Total to date (£)"],
        ["Pay",
         f"{p45_data.get('pay_this_employment', 0):,.2f}",
         f"{p45_data.get('pay_previous_employment', 0):,.2f}",
         f"{p45_data.get('total_pay_to_date', 0):,.2f}"],
        ["Tax",
         f"{p45_data.get('tax_this_employment', 0):,.2f}",
         f"{p45_data.get('tax_previous_employment', 0):,.2f}",
         f"{p45_data.get('total_tax_to_date', 0):,.2f}"],
        ["Student loan", "", "", f"{p45_data.get('student_loan_deductions', 0):,.2f}"],
    ], colWidths=[35*mm, 45*mm, 45*mm, 45*mm])
    pay_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(pay_tbl)
    elements.append(Spacer(1, 8*mm))

    elements.append(Paragraph(
        "This P45 must be given to your new employer. Keep Part 1A for your records.",
        ParagraphStyle('Note', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
    ))
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph(
        f"Generated by RealtouchHR on {datetime.now().strftime('%d %B %Y')}",
        ParagraphStyle('F', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(elements)
    return buffer.getvalue()


def generate_p60_pdf(employee: dict, company: dict, p60_data: dict) -> bytes:
    """
    Generate HMRC P60 - End of Year Certificate.
    
    p60_data keys:
      tax_year (e.g. '2024-25'),
      total_pay, total_tax, ni_letter, ni_contributions_breakdown (dict),
      student_loan_deductions, pay_previous_employment, tax_previous_employment,
      statutory_maternity_pay, statutory_paternity_pay, statutory_sick_pay
    """
    buffer, doc, styles = _base_doc("P60")
    title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER)
    sub_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, spaceAfter=4)
    elements = []

    tax_year = p60_data.get("tax_year", "")
    company_name = (company or {}).get("name", "Employer")
    emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}"

    elements.append(Paragraph(f"P60 End of Year Certificate - {tax_year}", title_style))
    elements.append(Paragraph(f"For the year ending 5 April {tax_year.split('-')[1] if '-' in tax_year else ''}", sub_style))
    elements.append(Spacer(1, 6*mm))

    # Employee/Employer block
    info_tbl = Table([
        ["Employee", emp_name, "Employer", company_name],
        ["NI number", employee.get("ni_number", ""), "PAYE reference", (company or {}).get("paye_reference", "")],
        ["Tax code", p60_data.get("tax_code", employee.get("tax_code", "")), "", ""],
    ], colWidths=[35*mm, 55*mm, 35*mm, 55*mm])
    info_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_tbl)
    elements.append(Spacer(1, 5*mm))

    # Pay and tax
    elements.append(Paragraph("Pay and Income Tax", h2))
    pay_tbl = Table([
        ["Description", "This employment (£)", "Previous employment (£)", "Total (£)"],
        ["Total pay",
         f"{p60_data.get('total_pay', 0):,.2f}",
         f"{p60_data.get('pay_previous_employment', 0):,.2f}",
         f"{p60_data.get('total_pay', 0) + p60_data.get('pay_previous_employment', 0):,.2f}"],
        ["Total tax deducted",
         f"{p60_data.get('total_tax', 0):,.2f}",
         f"{p60_data.get('tax_previous_employment', 0):,.2f}",
         f"{p60_data.get('total_tax', 0) + p60_data.get('tax_previous_employment', 0):,.2f}"],
    ], colWidths=[40*mm, 45*mm, 45*mm, 40*mm])
    pay_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ]))
    elements.append(pay_tbl)
    elements.append(Spacer(1, 5*mm))

    # NI
    elements.append(Paragraph("National Insurance contributions", h2))
    ni_rows = [["NI letter", "Earnings at LEL (£)", "Earnings above LEL up to PT (£)", "Earnings above PT up to UEL (£)", "Employee NI (£)"]]
    ni = p60_data.get("ni_contributions_breakdown", {}) or {}
    ni_rows.append([
        p60_data.get("ni_letter", "A"),
        f"{ni.get('earnings_at_lel', 0):,.2f}",
        f"{ni.get('earnings_lel_to_pt', 0):,.2f}",
        f"{ni.get('earnings_pt_to_uel', 0):,.2f}",
        f"{ni.get('employee_ni', 0):,.2f}",
    ])
    ni_tbl = Table(ni_rows, colWidths=[20*mm, 35*mm, 45*mm, 45*mm, 30*mm])
    ni_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ]))
    elements.append(ni_tbl)
    elements.append(Spacer(1, 5*mm))

    # Other deductions
    elements.append(Paragraph("Other", h2))
    other_tbl = Table([
        ["Student loan deductions", f"£{p60_data.get('student_loan_deductions', 0):,.2f}"],
        ["Statutory Maternity Pay", f"£{p60_data.get('statutory_maternity_pay', 0):,.2f}"],
        ["Statutory Paternity Pay", f"£{p60_data.get('statutory_paternity_pay', 0):,.2f}"],
        ["Statutory Sick Pay", f"£{p60_data.get('statutory_sick_pay', 0):,.2f}"],
    ], colWidths=[100*mm, 55*mm])
    other_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ]))
    elements.append(other_tbl)
    elements.append(Spacer(1, 8*mm))
    elements.append(Paragraph(
        "This P60 shows your total pay and deductions for the tax year. Keep it safe - you'll need it for tax returns.",
        ParagraphStyle('N', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
    ))
    elements.append(Paragraph(
        f"Generated by RealtouchHR on {datetime.now().strftime('%d %B %Y')}",
        ParagraphStyle('F', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(elements)
    return buffer.getvalue()


def generate_p11d_pdf(employee: dict, company: dict, p11d_data: dict) -> bytes:
    """
    Generate HMRC P11D - Return of Expenses and Benefits.
    
    p11d_data keys:
      tax_year, benefits (list of dicts with 'category', 'description', 'cash_equivalent')
    """
    buffer, doc, styles = _base_doc("P11D")
    title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER)
    sub_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, spaceAfter=4)
    elements = []

    tax_year = p11d_data.get("tax_year", "")
    emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}"
    company_name = (company or {}).get("name", "Employer")

    elements.append(Paragraph(f"P11D Expenses and Benefits - {tax_year}", title_style))
    elements.append(Paragraph("Return of Expenses Payments and Benefits", sub_style))
    elements.append(Spacer(1, 6*mm))

    info_tbl = Table([
        ["Employee", emp_name, "Employer", company_name],
        ["NI number", employee.get("ni_number", ""), "PAYE reference", (company or {}).get("paye_reference", "")],
    ], colWidths=[35*mm, 55*mm, 35*mm, 55*mm])
    info_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ]))
    elements.append(info_tbl)
    elements.append(Spacer(1, 5*mm))

    elements.append(Paragraph("Benefits in Kind", h2))
    benefits = p11d_data.get("benefits", []) or []
    rows = [["Category", "Description", "Cash equivalent (£)"]]
    total_cash = 0.0
    for b in benefits:
        cash = float(b.get("cash_equivalent", 0) or 0)
        total_cash += cash
        rows.append([b.get("category", ""), b.get("description", ""), f"{cash:,.2f}"])
    rows.append(["", "TOTAL", f"{total_cash:,.2f}"])

    bt = Table(rows, colWidths=[45*mm, 90*mm, 35*mm])
    bt.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e7ff')),
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ]))
    elements.append(bt)
    elements.append(Spacer(1, 8*mm))
    elements.append(Paragraph(
        "Class 1A National Insurance contributions are due on the total cash equivalent.",
        ParagraphStyle('N', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
    ))
    elements.append(Paragraph(
        f"Generated by RealtouchHR on {datetime.now().strftime('%d %B %Y')}",
        ParagraphStyle('F', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
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
