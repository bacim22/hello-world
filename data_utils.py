import pandas as pd
import pdfplumber
import io
import os
from typing import Dict

def parse_csv(content: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(content))

def parse_excel(content: bytes) -> Dict[str, pd.DataFrame]:
    xlsx = pd.ExcelFile(io.BytesIO(content))
    datasets = {}
    for sheet_name in xlsx.sheet_names:
        datasets[sheet_name] = xlsx.parse(sheet_name)
    return datasets

def parse_pdf(content: bytes) -> pd.DataFrame:
    tables = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                tables.append(df)
    if not tables:
        raise ValueError("No tables found in PDF.")
    return pd.concat(tables, ignore_index=True)

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                df[col] = df[col].str.replace(',', '').astype(float)
            except (ValueError, AttributeError):
                continue
    return df
