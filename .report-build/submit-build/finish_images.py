from pathlib import Path
import re,os,json,shutil,ast,subprocess,hashlib,csv
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
ROOT=Path(__file__).resolve().parents[2]
BUILD=Path(__file__).resolve().parent
OUT=ROOT/'Submit';IMAGES=ROOT/'images'
A=OUT/'作业1_需求调研成果';B=OUT/'作业2_需求建模成果'
TAG='9组-1011101011'
current={p.name:p for p in IMAGES.iterdir() if p.suffix in ['.png','.drawio']}
actual_outputs=[];superseded=json.loads((BUILD/'superseded_word_outputs.json').read_text(encoding='utf-8'));missing=[]
source=(BUILD/'update_images.py').read_text(encoding='utf-8')
source=source[source.index('# Reuse the existing A4 formatter'):]
exec(compile(source,'image_update_finish','exec'),globals())
