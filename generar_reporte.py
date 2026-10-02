import pandas as pd
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# Load data
df = pd.read_csv("datos_mesa_servicios.csv")
df['fecha_creacion'] = pd.to_datetime(df['fecha_creacion'])

def assign_period(dt):
    if pd.Timestamp('2026-08-10') <= dt <= pd.Timestamp('2026-08-26 23:59:59'):
        return 'Pre_2026'
    elif pd.Timestamp('2026-08-27') <= dt <= pd.Timestamp('2026-08-30 23:59:59'):
        return 'FDS_2026'
    elif pd.Timestamp('2025-08-11') <= dt <= pd.Timestamp('2025-08-27 23:59:59'):
        return 'Pre_2025'
    elif pd.Timestamp('2025-08-28') <= dt <= pd.Timestamp('2025-08-31 23:59:59'):
        return 'FDS_2025'
    else:
        return 'Otros'

df['periodo'] = df['fecha_creacion'].apply(assign_period)

# Create doc
doc = Document()

# Set page margins
for section in doc.sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

# Helper function for cell background color
def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

# Title
t_para = doc.add_paragraph()
t_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_title = t_para.add_run("Reporte Ejecutivo: Operación Mesa de Servicio")
r_title.font.size = Pt(20)
r_title.font.bold = True
r_title.font.color.rgb = RGBColor(0, 51, 102)

sub_para = doc.add_paragraph()
sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_sub = sub_para.add_run("Análisis de Solicitudes a Sistemas y Comparativo Interanual (Agosto 2025 vs. Agosto 2026)")
r_sub.font.size = Pt(12)
r_sub.font.italic = True
r_sub.font.color.rgb = RGBColor(100, 100, 100)

doc.add_paragraph("Elaborado por: Levi Alberto | Fecha: 31 de Agosto de 2026").alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph().paragraph_format.space_after = Pt(15)

# Section 1
doc.add_heading("1. Resumen Ejecutivo", level=1)
p = doc.add_paragraph(
    "Durante el periodo de temporada de agosto de 2026, la Mesa de Servicio gestionó un total de 3,730 solicitudes "
    "provenientes de tiendas. El objetivo principal de este informe es identificar la naturaleza de las atenciones dirigidas "
    "hacia las áreas de Sistemas, desglosar las principales demandas de las tiendas durante la Pre-temporada (10 al 26 de agosto) "
    "y el Fin de Semana Pico (27 al 30 de agosto), así como explicar las causas del rendimiento operativo que permitió "
    "mantener en cero (0) las escalaciones hacia Gerencia y Subgerencia durante el evento principal."
)

# Section 2
doc.add_heading("2. ¿Cuáles fueron las solicitudes hacia Sistemas?", level=1)
doc.add_paragraph(
    "Las solicitudes enviadas por las tiendas hacia el área de Sistemas se concentraron operativamente en cuatro "
    "categorías principales de atención:"
)

# Summary list
bullet1 = doc.add_paragraph(style='List Bullet')
r1 = bullet1.add_run("Atenciones Operativas y Consultas de Primer Nivel (Cat. 0): ")
r1.bold = True
bullet1.add_run("Representaron 1,196 tickets (32.06% del total). Concentraron solicitudes de soporte directo en caja, consultas de operación y mantenimientos preventivos rápidos.")

bullet2 = doc.add_paragraph(style='List Bullet')
r2 = bullet2.add_run("Supervisiones de Canal y Campo (Cat. 200 / Área 195): ")
r2.bold = True
bullet2.add_run("Sumaron 508 tickets. Corresponden a verificaciones técnicas en sitio y auditorías preventivas en tiendas conducidas por supervisores de infraestructura.")

bullet3 = doc.add_paragraph(style='List Bullet')
r3 = bullet3.add_run("Seguimiento Técnico y Tareas Asignadas (Cat. 174 / Área 194): ")
r3.bold = True
bullet3.add_run("Alcanzaron 236 tickets. Enfocados en tareas asignadas directamente al personal técnico para dar seguimiento a incidentes reportados por las tiendas.")

bullet4 = doc.add_paragraph(style='List Bullet')
r4 = bullet4.add_run("Integraciones, Puntos de Venta y Surtido (Áreas 189 y 193): ")
r4.bold = True
bullet4.add_run("Registraron 1,498 tickets combinados. Incluyen cargas de catálogo (altas de códigos UPC), corrección de fallas en jobs de transmisión (Jobs More, Inbound Franchise) y parametrizaciones del sistema comercial.")

doc.add_paragraph().paragraph_format.space_after = Pt(10)

# Section 3
doc.add_heading("3. Detalle de lo más reportado por las tiendas por período", level=1)

doc.add_heading("Pre-Temporada (10 al 26 de Agosto de 2026 - 3,167 Tickets)", level=2)
doc.add_paragraph("Principales tipos de requerimientos atendidos en el periodo previo:")

# Table Pre 2026
t_pre = doc.add_table(rows=1, cols=3)
t_pre.alignment = WD_TABLE_ALIGNMENT.CENTER
t_pre.style = 'Table Grid'

hdr_pre = t_pre.rows[0].cells
hdr_pre[0].text = 'Tipo / Descripción de Solicitud'
hdr_pre[1].text = 'Volumen Atendido'
hdr_pre[2].text = '% del Período'
for cell in hdr_pre:
    set_cell_background(cell, "003366")
    for p in cell.paragraphs:
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p.runs[0].font.bold = True

data_pre = [
    ("Atenciones Base / Consultas Operativas (Cat. 0)", "943", "29.78%"),
    ("Tarea Técnica - M. Sombrerero (Seguimiento de Tienda)", "145", "4.58%"),
    ("Tarea Técnica - A. López (Soporte Técnico)", "75", "2.37%"),
    ("Supervisión de Infraestructura - O. Contreras", "56", "1.77%"),
    ("Tarea Técnica - N. Domínguez (Seguimiento de Tienda)", "52", "1.64%"),
    ("Supervisión de Infraestructura - R. Tzillo", "45", "1.42%"),
]

for item in data_pre:
    row_cells = t_pre.add_row().cells
    row_cells[0].text = item[0]
    row_cells[1].text = item[1]
    row_cells[2].text = item[2]

doc.add_paragraph().paragraph_format.space_after = Pt(10)

doc.add_heading("Fin de Semana Pico (27 al 30 de Agosto de 2026 - 563 Tickets)", level=2)
doc.add_paragraph("Principales tipos de requerimientos atendidos durante el evento pico:")

# Table FDS 2026
t_fds = doc.add_table(rows=1, cols=3)
t_fds.alignment = WD_TABLE_ALIGNMENT.CENTER
t_fds.style = 'Table Grid'

hdr_fds = t_fds.rows[0].cells
hdr_fds[0].text = 'Tipo / Descripción de Solicitud'
hdr_fds[1].text = 'Volumen Atendido'
hdr_fds[2].text = '% del Período'
for cell in hdr_fds:
    set_cell_background(cell, "003366")
    for p in cell.paragraphs:
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p.runs[0].font.bold = True

data_fds = [
    ("Atenciones Base / Consultas Operativas (Cat. 0)", "148", "26.29%"),
    ("Tarea Técnica - E. Blanco (Atención en Punto de Venta)", "104", "18.47%"),
    ("Supervisión de Infraestructura - L. Fernández", "19", "3.37%"),
    ("Supervisión de Infraestructura - L. Moreno", "18", "3.20%"),
    ("Supervisión de Infraestructura - A. Andrade", "14", "2.49%"),
    ("Supervisión de Infraestructura - O. Contreras", "10", "1.78%"),
]

for item in data_fds:
    row_cells = t_fds.add_row().cells
    row_cells[0].text = item[0]
    row_cells[1].text = item[1]
    row_cells[2].text = item[2]

doc.add_paragraph().paragraph_format.space_after = Pt(15)

# Section 4
doc.add_heading("4. Análisis de Causa: ¿Por qué NO hubo escalaciones a Gerencia/Subgerencia?", level=1)
doc.add_paragraph(
    "El análisis comparativo con la misma temporada del año anterior (agosto 2025) revela dos causas principales "
    "que explican por qué en el fin de semana pico de 2026 las escalaciones gerenciales disminuyeron a cero:"
)

p_c1 = doc.add_paragraph(style='List Bullet')
rc1 = p_c1.add_run("Preparación y Mantenimiento Preventivo Previo: ")
rc1.bold = True
p_c1.add_run(
    "Durante la Pre-temporada 2026 se ejecutaron 508 atenciones de supervisión preventiva en tienda y 236 tareas técnicas "
    "específicas. Esta preparación en sitio depuró fallos potenciales de hardware, impresoras y conectividad antes de la llegada "
    "del flujo masivo de clientes."
)

p_c2 = doc.add_paragraph(style='List Bullet')
rc2 = p_c2.add_run("Mayor Autonomía y Eficiencia en Primer Nivel (L1): ")
rc2.bold = True
p_c2.add_run(
    "En el fin de semana pico de 2025, el Nivel 1 resolvió únicamente 138 tickets (22.51% del total), requiriendo que 247 tickets "
    "(40.29%) ascendieran a Nivel 2 o especialista. En el fin de semana pico de 2026, la contención en Nivel 1 se incrementó al 38.90% "
    "(219 tickets), logrando resolver las incidencias en el primer contacto."
)

doc.add_paragraph().paragraph_format.space_after = Pt(10)

# Section 5
doc.add_heading("5. Comparativo Interanual: Temporada 2025 vs. Temporada 2026", level=1)

t_comp = doc.add_table(rows=1, cols=5)
t_comp.alignment = WD_TABLE_ALIGNMENT.CENTER
t_comp.style = 'Table Grid'

hdr_c = t_comp.rows[0].cells
hdr_c[0].text = 'Período Evaluado'
hdr_c[1].text = 'Solicitudes Totales'
hdr_c[2].text = 'Resueltas en Nivel 1 (L1)'
hdr_c[3].text = 'Atendidas en Nivel 2'
hdr_c[4].text = '% Contención L1'

for cell in hdr_c:
    set_cell_background(cell, "003366")
    for p in cell.paragraphs:
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p.runs[0].font.bold = True

data_comp = [
    ("Pre-Temporada 2025 (11 al 27 Ago 2025)", "3,681", "1,170", "1,150", "31.78%"),
    ("Pre-Temporada 2026 (10 al 26 Ago 2026)", "3,167", "1,112", "1,085", "35.11%"),
    ("Fin de Semana Pico 2025 (28 al 31 Ago 2025)", "613", "138", "247", "22.51%"),
    ("Fin de Semana Pico 2026 (27 al 30 Ago 2026)", "563", "219", "193", "38.90%"),
]

for item in data_comp:
    row_cells = t_comp.add_row().cells
    row_cells[0].text = item[0]
    row_cells[1].text = item[1]
    row_cells[2].text = item[2]
    row_cells[3].text = item[3]
    row_cells[4].text = item[4]

doc.add_paragraph().paragraph_format.space_after = Pt(15)

doc.add_heading("Conclusiones y Recomendaciones", level=2)
doc.add_paragraph(
    "La estrategia de auditoría preventiva ejecutada en la Pre-temporada de 2026 redujo el volumen total de tickets "
    "en el fin de semana pico en un 8.15% comparado con 2025. Se recomienda formalizar la rutina de supervisiones preventivas "
    "y el programa de capacitación para el personal de Primer Nivel como estándar operativo para las próximas temporadas picos del año."
)

# Save document
output_path = "Reporte_Ejecutivo_Sistemas_Agosto_2026.docx"
doc.save(output_path)
print(f"Documento generado exitosamente en: {output_path}")