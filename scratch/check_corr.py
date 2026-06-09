import pandas as pd
import os

path = r"c:\Users\njana\Documents\e-vehicle_placement\data\EV_Fleet_Drivers.xlsx"
df = pd.read_excel(path, sheet_name="Correlation_Matrix")
print(df.iloc[1:, 0].dropna().tolist())
