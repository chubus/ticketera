"""
Generador de PDFs para tickets de Belgrano Ahorro Ticketera.

Este módulo utiliza ReportLab para generar PDFs profesionales de tickets
con toda la información del pedido, cliente y productos.
"""

from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import json
import logging

logger = logging.getLogger(__name__)


def format_currency(amount):
    """Formatea un monto como moneda argentina"""
    try:
        return f"${float(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "$0,00"


def format_datetime(dt):
    """Formatea una fecha/hora para mostrar"""
    if not dt:
        return "No especificada"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    return dt.strftime('%d/%m/%Y %H:%M')


def generate_ticket_pdf(ticket):
    """
    Genera un PDF para un ticket dado.
    
    Args:
        ticket: Objeto Ticket de SQLAlchemy
        
    Returns:
        BytesIO: Buffer con el contenido del PDF
    """
    buffer = BytesIO()
    
    # Crear documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para el título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para texto normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        fontName='Helvetica'
    )
    
    # Estilo para texto pequeño
    small_style = ParagraphStyle(
        'CustomSmall',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        fontName='Helvetica'
    )
    
    # Contenido del PDF
    story = []
    
    # ==================== ENCABEZADO ====================
    story.append(Paragraph("BELGRANO AHORRO", title_style))
    story.append(Paragraph("Ticket de Pedido", subtitle_style))
    story.append(Spacer(1, 0.2*inch))
    
    # ==================== INFORMACIÓN DEL TICKET ====================
    ticket_info_data = [
        ['Número de Ticket:', ticket.numero],
        ['Fecha de Creación:', format_datetime(ticket.fecha_creacion)],
        ['Estado:', ticket.estado.upper() if ticket.estado else 'PENDIENTE'],
        ['Prioridad:', ticket.prioridad.upper() if ticket.prioridad else 'NORMAL'],
    ]
    
    if ticket.repartidor_nombre:
        ticket_info_data.append(['Repartidor Asignado:', ticket.repartidor_nombre])
        if ticket.fecha_asignacion:
            ticket_info_data.append(['Fecha de Asignación:', format_datetime(ticket.fecha_asignacion)])
    
    ticket_info_table = Table(ticket_info_data, colWidths=[2.5*inch, 3.5*inch])
    ticket_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e5e7eb')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(ticket_info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # ==================== DATOS DEL CLIENTE ====================
    story.append(Paragraph("DATOS DEL CLIENTE", subtitle_style))
    
    cliente_data = [
        ['Nombre:', ticket.cliente_nombre or 'No especificado'],
        ['Dirección:', ticket.cliente_direccion or 'No especificada'],
        ['Teléfono:', ticket.cliente_telefono or 'No especificado'],
        ['Email:', ticket.cliente_email or 'No especificado'],
    ]
    
    cliente_table = Table(cliente_data, colWidths=[2.5*inch, 3.5*inch])
    cliente_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e5e7eb')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(cliente_table)
    story.append(Spacer(1, 0.3*inch))
    
    # ==================== PRODUCTOS ====================
    story.append(Paragraph("PRODUCTOS SOLICITADOS", subtitle_style))
    
    # Parsear productos
    try:
        if ticket.productos:
            if isinstance(ticket.productos, str):
                productos = json.loads(ticket.productos)
            else:
                productos = ticket.productos
        else:
            productos = []
    except:
        productos = []
        logger.error(f"Error parseando productos del ticket {ticket.id}")
    
    if productos:
        # Encabezado de la tabla de productos
        productos_data = [
            ['#', 'Producto', 'Cantidad', 'Precio Unit.', 'Subtotal']
        ]
        
        # Agregar cada producto
        total_general = 0
        for idx, producto in enumerate(productos, 1):
            nombre = producto.get('nombre', 'Producto sin nombre')
            cantidad = int(producto.get('cantidad', 0))
            precio = float(producto.get('precio', 0))
            subtotal = float(producto.get('subtotal', precio * cantidad))
            total_general += subtotal
            
            # Agregar información adicional si está disponible
            detalles = []
            if producto.get('negocio'):
                detalles.append(f"Negocio: {producto['negocio']}")
            if producto.get('sucursal'):
                detalles.append(f"Sucursal: {producto['sucursal']}")
            
            nombre_completo = f"{nombre}"
            if detalles:
                nombre_completo += f"\n<font size=8 color='#6b7280'>{' | '.join(detalles)}</font>"
            
            productos_data.append([
                str(idx),
                Paragraph(nombre_completo, normal_style),
                str(cantidad),
                format_currency(precio),
                format_currency(subtotal)
            ])
        
        # Fila de total
        productos_data.append([
            '', '', '', 
            Paragraph('<b>TOTAL:</b>', normal_style),
            Paragraph(f'<b>{format_currency(ticket.total if ticket.total else total_general)}</b>', normal_style)
        ])
        
        # Crear tabla
        productos_table = Table(
            productos_data,
            colWidths=[0.4*inch, 2.8*inch, 0.8*inch, 1*inch, 1*inch]
        )
        
        productos_table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Cuerpo
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
            ('ALIGN', (0, 1), (0, -2), 'CENTER'),  # Número centrado
            ('ALIGN', (1, 1), (1, -2), 'LEFT'),    # Nombre a la izquierda
            ('ALIGN', (2, 1), (-1, -2), 'RIGHT'),  # Cantidad, precio, subtotal a la derecha
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Fila de total
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fef3c7')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
            ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1e3a8a')),
            ('TOPPADDING', (0, -1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
        ]))
        
        story.append(productos_table)
    else:
        story.append(Paragraph("<i>No hay productos registrados</i>", small_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # ==================== INDICACIONES ====================
    if ticket.indicaciones:
        story.append(Paragraph("INDICACIONES ESPECIALES", subtitle_style))
        story.append(Paragraph(ticket.indicaciones, normal_style))
        story.append(Spacer(1, 0.2*inch))
    
    # ==================== PIE DE PÁGINA ====================
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
        small_style
    ))
    story.append(Paragraph(
        "Belgrano Ahorro - Sistema de Gestión de Pedidos",
        small_style
    ))
    
    # Construir PDF
    doc.build(story)
    
    # Preparar buffer para lectura
    buffer.seek(0)
    return buffer


if __name__ == "__main__":
    # Test básico
    print("PDF Generator para Belgrano Tickets")
    print("Módulo listo para usar")
